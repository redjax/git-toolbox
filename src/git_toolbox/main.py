from __future__ import annotations

import argparse
import logging
from pathlib import Path
import platform
import subprocess
import typing as t

log: logging.Logger = logging.getLogger("git_prune")
logging.getLogger("git").setLevel("WARNING")

from git_toolbox import git_ops
from git_toolbox.utils.env_utils import get_default_python, is_git_installed

import git

PYTHON_VERSION: str = get_default_python()
GIT_INSTALLED: bool = is_git_installed()


def program_args() -> list[tuple[list[str], dict[str, str]]] | None:
    """Define arguments for this script's parser.

    Usage:
        This method should be rewritten for each new script it's used in.
            The existing code can be used as a reference, but every script requires
            different args and the code in this function may not suit your script.

    Returns:
        (list[tuple[list[str], dict[str, str]]] | None): A tuple to be passed to the `parse_cli_args()` method, containing
            argument flags/actions/help strings.

    """
    ## Define list of args for script to parse
    add_args: list[tuple[list[str], dict[str, str]]] = [
        (
            ["--dry-run"],
            {
                "action": "store_true",
                "help": "Prevent any git operations from occurring, print messages indicating what would have happened.",
            },
        ),
        (
            ["-v", "--verbose"],
            {
                "action": "store_true",
                "help": "Set logging level to DEBUG.",
            },
        ),
        (
            ["-f", "--force"],
            {
                "action": "store_true",
                "help": "If GitPython module fails to delete branch with git branch -d and -D, attempt to delete the branch with the host's git using subprocess.",
            },
        ),
        (
            ["-r", "--repo-path"],
            {
                "type": str,
                "help": 'Specify the file path to the git repository. If no option is passed, uses ".", i.e. the directory where this script was run.',
                "nargs": "?",
                "const": ".",
                "default": ".",
            },
        ),
        (
            ["-p", "--protected-branches"],
            {
                "nargs": "+",
                "help": 'Specify additional protected branches. Can be used multiple times, i.e. -p "branch1" -p "branch2".',
                "metavar": "BRANCH",
            },
        ),
    ]

    return add_args


def parse_cli_args(
    program_name: str | None = __name__,
    usage: str | None = None,
    description: str | None = None,
    add_args: list[tuple[list[str], dict[str, str]]] | None = None,
) -> argparse.Namespace:
    """Parse arguments passed when this script runs.

    Usage:
        Call this function and assign it to a variable, like `args = parse_cli_args()`. Parsed
            args will be available via dot notation, for example an arg named `--verbose` will be available
            at `args.verbose`.

        Pass options/args as a list of tuples, see example of args/flags passed to `parse_cli_args(add_args=add_args)`:

        ```python title="Example add_args values" linenums="1"
            add_args = [
                (
                    ["-v", "--verbose"],
                    {
                        "action": "store_true",
                        "help": "Set logging level to DEBUG.",
                    },
                ),


                (
                    ["--name"],
                    {"type": str, "help": "Specify the name to be used in the operation."},
                ),
            ]
        ```

    Params:
        program_name (str): Name of the script/program for help menu.
        usage (str):  String describing how to call the app.
        description (str): Description of the script/program for help menu.
        add_args (list[tuple[list[str], dict[str, str]]] | None): List of tuples
            representing args to add to the parser.

    Returns:
        (argparse.Namespace): An object with parsed arguments. Arguments are accessible by their name, for
            example an argument `--verbose` is accessible at `args.verbose`. If an argument has a hyphen, like `--dry-run`,
            the hyphen becomes an underscore, i.e. `args.dry_run`.

    """
    parser = argparse.ArgumentParser(
        prog=program_name, usage=usage, description=description
    )

    ## Add arguments from add_args list
    if add_args:
        try:
            for flags, kwargs in add_args:

                parser.add_argument(*flags, **kwargs)
        except ValueError as parse_err:
            msg = ValueError(
                f"Error adding flag(s) '{flags}' to parser. Details: {parse_err}"
            )
            log.error(msg)

            raise parse_err
        except Exception as exc:
            msg = Exception(
                f"Unhandled exception adding argument to parser. Details: {exc}"
            )
            log.error(msg)

            raise exc

    else:
        ## Uncomment to add default arguments
        # parser.add_argument("--dry-run", action="store_true")
        # parser.add_argument("-v", "--verbose", action="store_true")

        pass

    args: argparse.Namespace = parser.parse_args()

    return args


def setup_logging(
    log_level: str = "INFO",
    log_msg_fmt: (
        str | None
    ) = "%(asctime)s | %(levelname)s | %(name)s.%(funcName)s():%(lineno)d |> %(message)s",
    log_msg_datefmt: str = "%Y-%M-%d %H:%m:%S",
) -> None:
    logging.basicConfig(
        level=log_level,
        format=log_msg_fmt,
        datefmt=log_msg_datefmt,
    )


def setup(
    log_msg_fmt: (
        str | None
    ) = "%(asctime)s | %(levelname)s | %(name)s.%(funcName)s():%(lineno)d |> %(message)s",
    log_msg_datefmt: str = "%Y-%M-%d %H:%m:%S",
) -> argparse.Namespace:
    """Run program setup.

    Params:
        log_msg_fmt (str): The format string for logging messages.
        log_msg_datefmt (str): The format for timestamps on logging messages.

    Returns:
        (argparse.Namespace): An object with parsed arguments. Arguments are accessible by their name, for
            example an argument `--verbose` is accessible at `args.verbose`. If an argument has a hyphen, like `--dry-run`,
            the hyphen becomes an underscore, i.e. `args.dry_run`.

    """
    add_args: list[tuple[list[str], dict[str, str]]] | None = program_args()
    args: argparse.Namespace = parse_cli_args(
        program_name="python -m git_prune",
        add_args=add_args,
        description="Delete local branches that have been removed from the remote. Use --dry-run to prevent any actions on git branches.",
    )

    setup_logging(
        log_level=args.log_level or "INFO",
        log_msg_datefmt=log_msg_datefmt,
        log_msg_fmt=log_msg_fmt,
    )

    log.debug(
        f"Repository path: {args.repo_path}, Dry run: {args.dry_run}, Verbose: {args.verbose}, Force: {args.force}"
    )

    return args


def main(
    repo_path: str = git_ops.DEFAULT_REPO_PATH,
    dry_run: bool = False,
    force: bool = False,
    protected_branches: list[str] = git_ops.PROTECTED_BRANCHES,
) -> list[str]:
    """Method to run when this script is called directly.

    Params:
        repo_path (str): (Default: ".") Path to the local git repository.
        dry_run (bool): If `True`, skip all operations that would alter git branches.
        force (bool): If `True`, when `git branch -d` fails, function will retry with `-D`.
            If this fails, a final attempt will be made using the host's `git` via `subprocess`.
        protected_branches (list[str]): List of branch names that will not be altered.

    Returns:
        (list[str]): A list of branches deleted from the local repository.

    """
    log.debug(f"Found git: {GIT_INSTALLED}")
    log.debug(f"Python version: {PYTHON_VERSION}")
    log.debug(f"Protected branches: {protected_branches}")

    try:
        repo: git.Repo = git_ops.get_repo_obj(repo_path)
    except git.InvalidGitRepositoryError as invalid_repo:
        msg = Exception(f"Path is not a git repository: '{repo_path}'. Exiting.")
        log.error(msg)

        exit(1)

    deleted_branches: list[str] = git_ops.clean_branches(
        repo=repo,
        dry_run=dry_run,
        force=force,
        protected_branches=protected_branches,
    )

    if deleted_branches:
        ## Re-check local branches
        _local_branches: list[str] = git_ops.get_local_branches(repo=repo)

        log.debug(f"Refreshed local branches: {_local_branches}")

    return deleted_branches


if __name__ == "__main__":
    ## Run argument parser & logging config, get list of args from cli
    args: argparse.Namespace = setup()
    ## Initialize list of branch names to add to PROTECTED_BRANCHES.
    #  Do not modify this list directly. Use extra_protected_branches.append("branch_name") on lines below
    extra_protected_branches: list[str] = []

    protected_branches: list[str] = (
        git_ops.PROTECTED_BRANCHES + extra_protected_branches
    )

    main(
        repo_path=args.repo_path,
        dry_run=args.dry_run,
        force=args.force,
        protected_branches=protected_branches,
    )
