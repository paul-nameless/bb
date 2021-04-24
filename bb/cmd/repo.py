import typer
from bb.utils import get

app = typer.Typer()

url = "https://api.bitbucket.org/2.0/repositories/{}"


@app.command()
def list(team: str):
    response = get(url.format(team))

    row = "{:<16} {:<16} {:<16} {:<16}"
    print(row.format("Name", "Owner", "Project", "Slug (repo)"))

    for repo in response["values"]:
        print(
            row.format(
                repo["name"],
                repo["owner"]["display_name"],
                repo["project"]["name"],
                repo["slug"],
            )
        )
