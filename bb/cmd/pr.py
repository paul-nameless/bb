import json
from enum import Enum, auto
from typing import List

import humanize
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
    post,
)
from dateutil.parser import parse
from rich import box
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table

app = typer.Typer()
prs_url = "https://api.bitbucket.org/2.0/repositories/{workspace}/{slug}/pullrequests"
merge_url = "https://api.bitbucket.org/2.0/repositories/{workspace}/{slug}/pullrequests/{id}/merge"
diff_url = "https://api.bitbucket.org/2.0/repositories/{workspace}/{slug}/pullrequests/{id}/diff"
pr_url = "https://api.bitbucket.org/2.0/repositories/{workspace}/{slug}/pullrequests/{id}"
approve_url = "https://api.bitbucket.org/2.0/repositories/{workspace}/{slug}/pullrequests/{id}/approve"


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
        created = humanize.naturaldate(parse(pr["created_on"]))
        updated = humanize.naturaldate(parse(pr["updated_on"]))
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
    data = {"title": title, "source": {"branch": {"name": src_branch}}, "close_source_branch": close}
    if dst_branch:
        data["destination"] = {"branch": {"name": dst_branch}}
    if reviewers:
        data["reviewers"] = [{"username": r} for r in reviewers]
    if body:
        data["description"] = body

    console = Console()
    with console.status("[bold green]Loading...") as status:
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
):
    url = merge_url.format(
        workspace=workspace, slug=slug, id=id
    )
    resp = post(url)
    handle_error(resp)
    print(resp["state"])


@app.command()
def status(
    workspace: str = get_workspace(),
    slug: str = get_slug(),
    state: State = State.OPEN,
):
    console = Console()
    with console.status("[bold green]Loading...") as status:
        response = get(
            prs_url.format(workspace=workspace, slug=slug), {"state": state}
        )
        table = generate_prs_table(response["values"], extra=True)
    console.print(table)


@app.command()
def diff(
    id: str,
    workspace: str = get_workspace(),
    slug: str = get_slug(),
):
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
    url = approve_url.format(
        workspace=workspace, slug=slug, id=id
    )
    console = Console()
    with console.status("[bold green]Loading...") as status:
        resp = post(url)
    handle_error(resp)
    print(reps["state"])
