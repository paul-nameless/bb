import typer
from bb.utils import get, get_workspace
from rich import box
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Get repo information")

repo_url = "https://api.bitbucket.org/2.0/repositories/{workspace}"


@app.command()
def list(
    workspace: str = get_workspace(),
):
    """
    List repositories in current workspace
    """
    console = Console()
    with console.status("[bold green]Loading...") as status:
        resp = get(repo_url.format(workspace=workspace))
        table = generate_repo_table(resp["values"])
    console.print(table)


def generate_repo_table(repos) -> Table:
    table = Table(box=box.SIMPLE)
    columns = [
        "Project",
        "Slug",
        "Owner"
    ]
    for column in columns:
        table.add_column(column, justify="left", style="cyan", no_wrap=True)

    for repo in repos:
        table.add_row(
            repo["project"]["name"],
            repo["slug"],
            repo["owner"]["display_name"],
        )
    return table
