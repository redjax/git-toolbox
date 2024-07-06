"""Cleanup your local git environment.

Description:
    This script compares git branches in a specified repository path,
    defaulting to the directory this script is run from i.e. ".",
    with branches on the remote, deleting any local branches not found on the remote.

    This helps by cleaning up branches that have been deleted from the remote, for example a merged feature or fix.
    
    By default, the script will not touch the following branches if they are found, regardless of their presence on the remote:
        - main
        - master
        - dev
        - rc
        - gh-pages
    
    See the `Usage` section for instructions on passing CLI args, adding more protected branch names, etc.

Usage:
    Run this script as a module, i.e. `python -m git_prune <args>`. To see available args and their description, run `python -m git_prune -h`.
    
    ## Prevent accidental deletions with `--dry-run`
    
    Run the script with `--dry-run` to prevent modifications on local branches,
    instead printing a message describing the action that would have been taken.

    ## Pass protected branches with `nargs`
    
    To add more branches that should be ignored in the local repository,
    you can either modify the `PROTECTED_BRANCHES` list below (not recommended),
    or you can pass additional protected branches with `-p`.
    
    For example, to protect the branches `ci` and `stage`, you would run `python -m git_prune -r <repo_path> -p "ci" -p "stage".
    
    ## Attempt to force deletion
    
    `git_prune` will first attempt to delete a branch with `git branch -d <branch>`. If this fails and you passed the `-f/--force` flag,
    a retry attempt will be made using `git branch -D <branch>`. If this also fails, a third and final attempt will be made using the host's
    git by running the command `git branch -D <branch>` through the `subprocess.run()` command.

"""

from __future__ import annotations

from .main import main
