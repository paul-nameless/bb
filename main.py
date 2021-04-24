"""
b pr list
b pr create
b pr merge
b pr info #12
"""
from cmd import pr, repo

import typer

app = typer.Typer()

app.add_typer(pr.app, name="pr")
app.add_typer(repo.app, name="repo")

if __name__ == "__main__":
    app()
