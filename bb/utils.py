import json
import os
import subprocess
from functools import lru_cache

import humanize
import requests
from bb import config
from dateutil.parser import parse
from dateutil.tz import tzlocal
from rich.console import Console
from rich.syntax import Syntax


def get(url, query: dict = None):
    return requests.get(url, auth=config.AUTH, params=query).json()

def get_text(url, query: dict = None):
    return requests.get(url, auth=config.AUTH, params=query).text

def post(url: str, data: dict = None):
    return requests.post(url, auth=config.AUTH, json=data).json()


def handle_error(resp: dict):
    if resp.get("type") == "error":
        syntax = Syntax(
            json.dumps(resp),
            "json",
            theme=config.THEME,
            background_color=config.BG_COLOR,
        )
        console = Console()
        console.print(syntax)
        exit(1)


def run_cmd(cmd: list):
    proc = subprocess.run(
        cmd,
        cwd=os.getenv("PWD"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        print(f"{cmd} exited with {proc.returncode} code")
        print(proc.stderr.decode())
        exit(1)
    return proc.stdout.decode().strip()


@lru_cache(maxsize=1)
def get_url():
    return run_cmd(["git", "remote", "get-url", "origin"])


def get_workspace():
    url = get_url()
    return url.split(":")[-1].split("/")[0]


def get_slug():
    url = get_url()
    return url.split("/")[-1].split(".")[0]


def get_last_commit_msg():
    return run_cmd(["git", "log", "-1", "--pretty=%B"])


def get_current_branch():
    return run_cmd(
        ["git", "branch", "--show-current"],
    )


def pp(d: dict):
    syntax = Syntax(
        json.dumps(d, indent=4, sort_keys=True),
        "json",
        theme=config.THEME,
        background_color=config.BG_COLOR,
    )
    console = Console()
    console.print(syntax)


def parse_dt(dt) -> str:
    dt = parse(dt)
    dt = dt.astimezone(tzlocal()).replace(tzinfo=None)
    return humanize.naturaltime(dt)
