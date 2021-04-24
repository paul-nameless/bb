import typer
from bb.cmd import pr, repo

app = typer.Typer()

app.add_typer(pr.app, name="pr")
app.add_typer(repo.app, name="repo")

if __name__ == "__main__":
    app()
