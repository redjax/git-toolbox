from __future__ import annotations

import logging
from pathlib import Path
import typing as t

log = logging.getLogger("git_toolbox.cli.cli_main")

from git_toolbox import git_ops
from git_toolbox.cli._cli_git.clean import clean_app

from cyclopts import App, Parameter, validators
import git

cli_app = App(
    name="git-toolbox",
    help="Python utility to script git actions. Uses GitPython for git operations. Run with -h to see help menu.",
    version="0.1.0",
)

cli_app.command(clean_app)


@cli_app.meta.default
def cli_launcher(
    *tokens: t.Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
    repo_path: str = ".",
):
    assert repo_path, ValueError("Missing a path to a git repository.")

    if not git_ops.git_dir_exists(repo_path=repo_path):
        log.error(
            git.InvalidGitRepositoryError(
                f"No .git repository directory found at path '{Path(repo_path).resolve()}'."
            )
        )
        exit(1)

    try:
        cli_app(tokens)
    except Exception as exc:
        msg = Exception(f"Unhandled exception executing CLI app. Details: {exc}")
        log.error(msg)

        raise exc
