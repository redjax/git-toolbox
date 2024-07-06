from __future__ import annotations

import logging
from pathlib import Path
import subprocess

log = logging.getLogger("git_toolbok.git_ops.methods")

from .constants import PROTECTED_BRANCHES

import git


def append_protected_branch(
    protected_branches: list[str] = PROTECTED_BRANCHES, append_branch: str = None
) -> list[str]:
    """Add a branch to the existing list of protected branch names.

    Params:
        protected_branches (list[str]): Existing list of protected branch names.
        append_branch (str): Name of branch to append to list of protected branch names.

    Returns:
        (list[str]): A list of strings representing git branch names that should not be altered.

    """
    if protected_branches is None:
        ## Initialize empty list
        protected_branches: list[str] = []

    if append_branch is None:
        ## No branch names to append, return protected_branches
        return protected_branches

    else:
        ## Append branch and return
        protected_branches.append(append_branch)
        return protected_branches


def git_dir_exists(repo_path: str = None) -> bool:
    """Search repository path for .git directory.

    Params:
        repo_path (str): (Default: ".") Path to the local git repository.

    Returns:
        (True): If a `.git/` directory is found in the `repo_path` directory.
        (False): If a `.git/` directory is not found in the `repo_path` directory.
    """
    return Path(f"{repo_path}/.git").exists()


def get_local_branches(repo: git.Repo = None) -> list[str]:
    """Get list of branch names detected in local repository.

    Params:
        repo (git.Repo): An initialized `git.Repo` instance.

    Returns:
        (list[str]): List of local git branches.

    """
    log.debug(f"Repo heads: {repo.heads}")
    if repo.heads is None or len(repo.heads) == 0:
        msg = f"No remotes found for repository at path '{repo.working_dir}'."
        log.error(msg)

        raise git.InvalidGitRepositoryError(msg)

    ## Get a list of local branches
    local_branches: list[str] = [head.name for head in repo.heads]

    return local_branches


def get_remote_branches(repo: git.Repo = None) -> list[str]:
    """Get list of branch names detected in remote repository.

    Params:
        repo (git.Repo): An initialized `git.Repo` instance.

    Returns:
        (list[str]): List of remote git branches.

    """
    ## Get a list of remote branches
    remote_branches: list[str] = [
        ref.name.replace("origin/", "") for ref in repo.remotes.origin.refs
    ]

    return remote_branches


def get_delete_branches(
    repo: git.Repo = None,
    local_branches: list[str] = None,
    remote_branches: list[str] = None,
    protected_branches: list[str] = PROTECTED_BRANCHES,
) -> list[str]:
    """Compare local & remote git branches, return list of branch names to delete.

    Params:
        repo (git.Repo): An initialized `git.Repo` instance. Needed for instances where
            local_branches or remote_branches are empty/None.
        local_branches (list[str]): List of branch names found in local repository.
        remote_branches (list[str]): List of branch names found in remote repository.
        protected_branches (list[str]): List of branch names that will not be altered.

    Returns:
        (list[str]): List of git branches to delete from local repository.

    """
    if local_branches is None or remote_branches is None:
        if repo is None:
            raise ValueError(
                "Missing list of local and/or remote branch names, and no git.Repo object detected. Cannot determine list of branches."
            )

    if local_branches is None:
        ## Get list of local branch names
        local_branches = get_local_branches(repo=repo)

    if remote_branches is None:
        ## Get list of remote branch names
        remote_branches = get_remote_branches(repo=repo)

    ## Find local branches that are not present in remote branches
    branches_to_delete: list[str] = [
        branch
        for branch in local_branches
        if (branch not in remote_branches) and (branch not in protected_branches)
    ]

    return branches_to_delete


def delete_branches(
    repo: git.Repo = None,
    branches_to_delete: list[str] = None,
    force: bool = False,
    protected_branches: list[str] = PROTECTED_BRANCHES,
) -> list[str]:
    """Run git branch delete operation on list of branches.

    Params:
        repo (git.Repo): An initialized `git.Repo` instance.
        branches_to_delete (list[str]): List of branches to delete from local repository.
        force (bool): If `True`, delete operations will be retried if they fail. The first attempt will retry using
            the `-d` flag, and if that fails the function will attempt to use the host's `git` via `subprocess`.
        protected_branches (list[str]): List of branch names that will not be altered.

    Returns:
        (list[str]): The list of branches deleted from the local repository.

    """
    deleted_branches: list[str] = []

    ## Iterate over list of branches to delete
    for branch in branches_to_delete:
        ## Avoid deleting specified branches
        if branch not in protected_branches:
            try:
                repo.git.branch("-d", branch)
                log.info(f"Deleted branch '{branch}'")

                deleted_branches.append(branch)

            except git.GitError as git_err:
                msg = Exception(
                    f"Git error while deleting branch '{branch}'. Details: {git_err}"
                )

                ## Retry with -D if force=True
                if force:
                    log.warning(
                        "First attempt failed, but force=True. Attempting to delete with -D"
                    )
                    try:
                        repo.git.branch("-D", branch)
                        log.info(f"Force-deleted branch '{branch}'")

                        deleted_branches.append(branch)

                    except git.GitError as git_err2:
                        msg2 = Exception(
                            f"Git error while force deleting branch '{branch}'. Details: {git_err2}"
                        )
                        log.warning(
                            f"Branch '{branch}' was not deleted. Reason: {msg2}"
                        )

                        ## Retry with subprocess
                        try:
                            log.info("Retrying one more time using subprocess.")
                            subprocess.run(["git", "branch", "-D", branch], check=True)
                            log.info(
                                f"Force-deleted branch '{branch}'. Required fallback to subprocess."
                            )

                            deleted_branches.append(branch)

                        except subprocess.CalledProcessError as git_err3:
                            msg3 = f"Git error while force deleting branch '{branch}' using subprocess. Details: {git_err3}"
                            log.warning(
                                f"Branch '{branch}' was not deleted. Reason: {msg3}"
                            )

                        except Exception as exc:
                            msg = f"Unhandled exception attempting to delete git branch '{branch}' using subprocess.run(). Details: {exc}"
                            log.error(msg)

                ## force=false, do not retry with Subprocess
                else:
                    log.warning(f"Branch '{branch}' was not deleted. Reason: {msg}")

                continue

    return deleted_branches


def clean_branches(
    repo: git.Repo = None,
    dry_run: bool = False,
    force: bool = False,
    protected_branches: list[str] = PROTECTED_BRANCHES,
) -> list[str] | None:
    """Params:
        repo (git.Repo): An initialized `git.Repo` instance.
        dry_run (bool): If `True`, skip all operations that would alter git branches.
        force (bool): If `True`, when `git branch -d` fails, function will retry with `-D`.
            If this fails, a final attempt will be made using the host's `git` via `subprocess`.
        protected_branches (list[str]): List of branch names that will not be altered.

    Returns:
        (list[str]): List of branches deleted from local repository.

    """

    log.info("Cleaning local branches that have been deleted from the remote.")

    ## Get list of branch names in local repository
    local_branches: list[str] = get_local_branches(repo=repo)
    log.info(f"Found [{len(local_branches)}] local branch(es).")

    if len(local_branches) < 15:
        ## Print local branches if there are less than 15
        log.debug(f"Local branches: {local_branches}")

    ## Get list of branch names in remote repository
    remote_branches: list[str] = get_remote_branches(repo=repo)
    log.info(f"Found [{len(remote_branches)}] remote branch(es).")

    if len(remote_branches) < 15:
        ## Print remote branches if there are less than 15
        log.debug(f"Remote branches: {remote_branches}")

    ## Compare local & remote branches, return list of branches in local that are not in remote
    branches_to_delete: list[str] = get_delete_branches(
        local_branches=local_branches,
        remote_branches=remote_branches,
        protected_branches=protected_branches,
    )
    log.info(f"Prepared [{len(branches_to_delete)}] branch(es) for deletion.")

    if len(branches_to_delete) < 15:
        ## Print branches to delete if there are less than 15
        log.debug(f"Deleting branches: {branches_to_delete}")

    ## Terminate early if dry_run=True
    if dry_run:
        log.warning("dry_run=True, terminating early to avoid accidental deletion.")
        log.warning(f"Would have deleted [{len(branches_to_delete)}] branch(es).")
        for b in branches_to_delete:
            log.warning(f"[DRY RUN] Would delete branch: {b}")

        return

    else:
        ## Delete local branches
        try:
            deleted_branches: list[str] = delete_branches(
                repo=repo,
                branches_to_delete=branches_to_delete,
                protected_branches=protected_branches,
                force=force,
            )

            return deleted_branches
        except Exception as exc:
            msg = Exception(
                f"Unhandled exception deleting git branches. Details: {exc}"
            )
            log.error(msg)

            raise exc


def get_repo_obj(repo_path: str = None) -> git.Repo:
    """Initialize a `GitPython` `git.Repo` object from a path.

    Params:
        repo_path (str): (Default: ".") Path to the local git repository.

    Returns:
        (git.Repo): An initialized `git.Repo` object for the given `repo_path`.
    """
    ## Initialize repository
    try:
        repo = git.Repo(path=repo_path)
    except git.InvalidGitRepositoryError as invalid_repo:
        msg = Exception(
            f"Path '{repo_path}' is not a Git repository. Details: {invalid_repo}"
        )
        log.warning(msg)

        raise git.InvalidGitRepositoryError
    except Exception as exc:
        msg = Exception(
            f"Unhandled exception initializing git.Repo object for repository path '{repo_path}'. Details: {exc}"
        )
        log.error(msg)

        raise exc

    ## Fetch latest changes & prune deleted branches
    try:
        repo.git.fetch("--prune")
    except Exception as exc:
        msg = Exception(
            f"Unhandled exception fetching branches from remote. Details: {exc}"
        )
        log.error(msg)

        raise exc

    return repo
