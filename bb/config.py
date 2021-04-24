import runpy
from pathlib import Path

CONFIG_DIR = Path("~/.config/bb/").expanduser()
CONFIG_FILE = CONFIG_DIR / "conf.py"

THEME = "emacs"
BG_COLOR = "default"
AUTH = None


if CONFIG_FILE.is_file():
    config_params = runpy.run_path(CONFIG_FILE)
    for param, value in config_params.items():
        if param.isupper():
            globals()[param] = value
else:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    print(
        "Enter bitbucket app user and password (https://bitbucket.org/account/settings/app-passwords/):"
    )
    user = input("user> ")
    pswd = input("pswd> ")
    AUTH = (user, pswd)

    CONFIG_FILE.write_text(f"AUTH = {AUTH}\n")
