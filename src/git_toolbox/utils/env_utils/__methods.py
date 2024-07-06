from __future__ import annotations

import platform


def get_default_python() -> str:
    """Detect Python version from environment.

    Returns:
        (str): The detected Python version, in format 'major.minor' i.e. '3.11'.

    """
    pyver_tuple: tuple[str, str, str] = platform.python_version_tuple()
    pyver: str = f"{pyver_tuple[0]}.{pyver_tuple[1]}"

    return pyver


def is_git_installed() -> bool:
    """Detect GitPython package.

    Returns:
        (True): If `GitPython` package is detected in environment.
        (False): If `GitPython` package is not detected in environment.

    """
    try:
        import git

        return True
    except ImportError:
        return False
