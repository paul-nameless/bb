import json
from enum import Enum, auto
from typing import List

import typer
from bb import config
from bb.utils import (
    get,
    get_current_branch,
    get_last_commit_msg,
    get_slug,
    get_text,
    get_workspace,
    handle_error,
    parse_dt,
    post,
    pp,
    run_cmd,
)
from dateutil.parser import parse
from rich import box
from rich.console import Console
from rich.markdown import Markdown
from rich.padding import Padding
from rich.syntax import Syntax
from rich.table import Table

app = typer.Typer(help="Manage pull requests")
prs_url = "https://api.bitbucket.org/2.0/repositories/{workspace}/{slug}/pullrequests"
merge_url = f"{prs_url}/{{id}}/merge"
diff_url = f"{prs_url}/{{id}}/diff"
pr_url = f"{prs_url}/{{id}}"
approve_url = f"{prs_url}/{{id}}/approve"
decline_url = f"{prs_url}/{{id}}/decline"
request_changes_url = f"{prs_url}/{{id}}/request-changes"
comments_url = f"{prs_url}/{{id}}/comments"
commits_url = f"{prs_url}/{{id}}/commits"


class State(str, Enum):
    def _generate_next_value_(name, start, count, last_values):
        return name

    MERGED = auto()
    SUPERSEDED = auto()
    OPEN = auto()
    DECLINED = auto()


@app.command()
def list(
    workspace: str = get_workspace(),
    slug: str = get_slug(),
    state: State = State.OPEN,
):
    """List all PRs"""
    console = Console()
    with console.status("[bold green]Loading...") as status:
        response = get(
            prs_url.format(workspace=workspace, slug=slug), {"state": state}
        )
        table = generate_prs_table(response["values"])
    console.print(table)


def generate_prs_table(prs: List[dict], extra: bool = False) -> Table:
    table = Table(box=box.SIMPLE)

    columns = [
        "Id",
        "Title",
        "Branch",
        "Created",
        "Updated",
        "Author",
    ]
    if extra:
        columns.extend(["Build", "Approved"])
    for column in columns:
        table.add_column(column, justify="left", style="cyan", no_wrap=True)

    for pr in prs:
        created = parse_dt(pr["created_on"])
        updated = parse_dt(pr["updated_on"])
        branch = f'{pr["source"]["branch"]["name"]}->{pr["destination"]["branch"]["name"]}'

        title = pr["title"] if len(pr["title"]) <= 32 else f"{pr['title'][:29]}..."
        row = [
            str(pr["id"]),
            title,
            branch,
            created,
            updated,
            pr["author"]["display_name"],
        ]
        if extra:
            build_status_resp = get(pr["links"]["statuses"]["href"])
            build_status = ",".join(
                (f'[red]it["state"]' if "fail" in it["state"] else f'[green]{it["state"]}' for it in build_status_resp["values"])
            )

            approve_resp = get(pr["links"]["self"]["href"])
            approve = ",".join(
                (it["user"]["display_name"] for it in approve_resp["participants"] if it["approved"])
            )
            approve = f"[green]{approve}"

            row.extend([build_status, approve])
        table.add_row(*row)
    return table



@app.command()
def create(
    workspace: str = get_workspace(),
    slug: str = get_slug(),
    title: str = get_last_commit_msg(),
    src_branch: str = get_current_branch(),
    dst_branch: str = None,
    reviewers: List[str] = [],
    body: str = None,
    close: bool = True,
):
    """Create new PR"""
    data = {"title": title, "source": {"branch": {"name": src_branch}}, "close_source_branch": close}
    if dst_branch:
        data["destination"] = {"branch": {"name": dst_branch}}
    if reviewers:
        data["reviewers"] = [{"username": r} for r in reviewers]
    if body:
        data["description"] = body

    console = Console()
    with console.status("[bold green]Loading...") as status:
        run_cmd(["git", "push", "origin", src_branch])
        resp = post(prs_url.format(workspace=workspace, slug=slug), data)
        handle_error(resp)

        table = generate_prs_table([resp])
    console.print(table)
    print(resp["links"]["html"]["href"])



@app.command()
def merge(
    id: str,
    workspace: str = get_workspace(),
    slug: str = get_slug(),
    delete_branch: bool = True,
):
    """Merge PR by ID"""
    url = merge_url.format(
        workspace=workspace, slug=slug, id=id
    )
    resp = post(url)
    handle_error(resp)
    print(resp["state"].title())
    if delete_branch:
        dst_branch = resp["destination"]["branch"]["name"]
        run_cmd(["git", "checkout", dst_branch])
        src_branch = resp["source"]["branch"]["name"]
        run_cmd(["git", "branch", "-D", src_branch])



@app.command()
def status(
    workspace: str = get_workspace(),
    slug: str = get_slug(),
    state: State = State.OPEN,
):
    """Shows more detailed information about PRs (Build, Approved)
    but slower than <bb pr list>"""
    console = Console()
    with console.status("[bold green]Loading...") as status:
        response = get(
            prs_url.format(workspace=workspace, slug=slug), {"state": state}
        )
        # TODO: show number of comments
        table = generate_prs_table(response["values"], extra=True)
    console.print(table)


@app.command()
def diff(
    id: str,
    workspace: str = get_workspace(),
    slug: str = get_slug(),
):
    """Show diff by PR ID"""
    url = diff_url.format(
        workspace=workspace,
        slug=slug,
        id=id,
    )
    console = Console()
    with console.status("[bold green]Loading...") as status:
        diff = get_text(url)
        syntax = Syntax(
            diff, "diff", theme=config.THEME, background_color=config.BG_COLOR
        )
    console.print(syntax)


@app.command()
def checkout(
    id: str,
    workspace: str = get_workspace(),
    slug: str = get_slug(),
):
    """Checkout PR by ID"""
    url = pr_url.format(
        workspace=workspace, slug=slug, id=id
    )
    console = Console()
    with console.status("[bold green]Loading...") as status:
        resp = get(url)
    branch_name = resp["source"]["branch"]["name"]
    run_cmd(["git", "checkout", "-b", branch_name])
    run_cmd(["git", "pull", "origin", branch_name])


@app.command()
def approve(
    id: str,
    workspace: str = get_workspace(),
    slug: str = get_slug(),
):
    """Approve PR by ID"""
    url = approve_url.format(
        workspace=workspace, slug=slug, id=id
    )
    console = Console()
    with console.status("[bold green]Loading...") as status:
        resp = post(url)
    handle_error(resp)
    print(resp["state"].title())


@app.command()
def decline(
    id: str,
    workspace: str = get_workspace(),
    slug: str = get_slug(),
):
    """Decline PR by ID"""
    url = decline_url.format(
        workspace=workspace, slug=slug, id=id
    )
    console = Console()
    with console.status("[bold green]Loading...") as status:
        resp = post(url)
    handle_error(resp)
    print(resp["state"].title())


@app.command()
def request_changes(
    id: str,
    workspace: str = get_workspace(),
    slug: str = get_slug(),
):
    """Request changes for PR by ID"""
    url = request_changes_url.format(
        workspace=workspace, slug=slug, id=id
    )
    console = Console()
    with console.status("[bold green]Loading...") as status:
        resp = post(url)
    handle_error(resp)
    print(resp["state"].title())


@app.command()
def comments(
    id: str,
    workspace: str = get_workspace(),
    slug: str = get_slug(),
):
    """View comments for PR by ID"""
    url = comments_url.format(
        workspace=workspace, slug=slug, id=id
    )
    console = Console()
    with console.status("[bold green]Loading...") as status:
        resp = get(url)
        handle_error(resp)

    for comment in resp["values"]:
        user = comment["user"]["display_name"]
        updated = parse_dt(comment["updated_on"])
        path = comment["inline"]["path"]
        # _from = comment["inline"]["from"] or ""
        to = comment["inline"]["to"] or ""
        line = f":{to}" if to else ""
        deleted = "(Deleted)" if comment["deleted"] else ""
        console.print(f"[bold]{user}[/bold] {path}{line} [dim]{updated}[/dim] {deleted}")
        markdown = comment["content"]["raw"]
        console.print(Padding(Markdown(markdown, code_theme=config.THEME), 1))


@app.command()
def commits(
    id: str,
    workspace: str = get_workspace(),
    slug: str = get_slug(),
):
    """View commits of PR by ID"""
    url = commits_url.format(
        workspace=workspace, slug=slug, id=id
    )
    console = Console()
    with console.status("[bold green]Loading...") as status:
        resp = get(url)
        handle_error(resp)

    for commit in resp["values"]:
        hash = commit["hash"]
        author = commit["author"]["raw"]
        date = commit["date"]
        message = commit["message"]

        console.print(f"[bold]commit {hash}[/bold]")
        console.print(f"[cyan]Author: {author}")
        console.print(f"[cyan]Date: {date}")
        console.print(Padding(message.strip(), (1, 4)))
