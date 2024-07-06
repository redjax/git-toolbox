from __future__ import annotations

import argparse
import logging

log = logging.getLogger("git_toolbox")

from git_toolbox import cli
from git_toolbox.git_ops.constants import PROTECTED_BRANCHES
from git_toolbox.main import main, setup, setup_logging

if __name__ == "__main__":
    setup_logging(log_level="DEBUG")
    # ## Run argument parser & logging config, get list of args from cli
    # args: argparse.Namespace = setup()
    # ## Initialize list of branch names to add to PROTECTED_BRANCHES.
    # #  Do not modify this list directly. Use extra_protected_branches.append("branch_name") on lines below
    # extra_protected_branches: list[str] = []

    # protected_branches: list[str] = PROTECTED_BRANCHES + extra_protected_branches
    # main(
    #     repo_path=args.repo_path,
    #     dry_run=args.dry_run,
    #     force=args.force,
    #     protected_branches=protected_branches,
    # )

    cli.cli_app.meta()
