from __future__ import annotations

import logging
from pathlib import Path
import typing as t

log = logging.getLogger("git_toolbox.cli._cli_git.clean.local")

from git_toolbox import git_ops

from cyclopts import App, Parameter, validators
import git

clean_local_app = App(
    name="local", group="Git Clean", help="Local git cleanup operations."
)


@clean_local_app.command(
    name="branches",
    help="Delete local branches that have been removed from the remote.",
    group="local",
)
def clean_local_branches(repo_path: str = "."):
    log.debug(f"Repository path: '{repo_path}'")

    repo = git_ops.get_repo_obj(repo_path=repo_path)

    try:
        git_ops.clean_branches(repo=repo)
    except git.InvalidGitRepositoryError as invalid_repo:
        log.error(invalid_repo)
        exit(1)
    except Exception as exc:
        msg = Exception(
            f"Unhandled exception cleaning local git branches. Details: {exc}"
        )
        log.error(msg)

        raise exc
