from __future__ import annotations

import logging
import logging.config
import logging.handlers
import os
from pathlib import Path
import platform
import shutil

import nox

## Detect container env, or default to False
if "CONTAINER_ENV" in os.environ:
    CONTAINER_ENV: bool = os.environ["CONTAINER_ENV"]
else:
    CONTAINER_ENV: bool = False


def setup_nox_logging(
    level_name: str = "DEBUG", disable_loggers: list[str] | None = []
) -> None:
    """Configure a logger for the Nox module.

    Params:
        level_name (str): The uppercase string repesenting a logging logLevel.
        disable_loggers (list[str] | None): A list of logger names to disable, i.e. for 3rd party apps.
            Note: Disabling means setting the logLevel to `WARNING`, so you can still see errors.

    """
    ## If container environment detected, default to logging.DEBUG
    if CONTAINER_ENV:
        level_name: str = "DEBUG"

    logging_config: dict = {
        "version": 1,
        "disable_existing_loggers": False,
        "loggers": {
            "nox": {
                "level": level_name.upper(),
                "handlers": ["console"],
                "propagate": False,
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "nox",
                "level": "DEBUG",
                "stream": "ext://sys.stdout",
            }
        },
        "formatters": {
            "nox": {
                "format": "[NOX] [%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
                "datefmt": "%Y-%m-%D %H:%M:%S",
            }
        },
    }

    ## Configure logging. Only run this once in an application
    logging.config.dictConfig(config=logging_config)

    ## Disable loggers by name. Sets logLevel to logging.WARNING to suppress all but warnings & errors
    for _logger in disable_loggers:
        logging.getLogger(_logger).setLevel(logging.WARNING)


setup_nox_logging(disable_loggers=[])

## Create logger for this module
log: logging.Logger = logging.getLogger("nox")

log.info(f"[container_env:{CONTAINER_ENV}]")

nox.options.default_venv_backend = "venv"
nox.options.reuse_existing_virtualenvs = True
nox.options.error_on_external_run = False
nox.options.error_on_missing_interpreters = False
# nox.options.report = True

## Define sessions to run when no session is specified
nox.sessions = ["lint", "export", "tests"]

# INIT_COPY_FILES: list[dict[str, str]] = [
#     {"src": "config/.secrets.example.toml", "dest": "config/.secrets.toml"},
#     {"src": "config/settings.toml", "dest": "config/settings.local.toml"},
# ]
## Define versions to test
PY_VERSIONS: list[str] = ["3.12", "3.11"]
## Set PDM version to install throughout
PDM_VER: str = "2.16.1"
## Set paths to lint with the lint session
LINT_PATHS: list[str] = ["src", "tests", "./noxfile.py"]

## Get tuple of Python ver ('maj', 'min', 'mic')
PY_VER_TUPLE = platform.python_version_tuple()
## Dynamically set Python version
DEFAULT_PYTHON: str = f"{PY_VER_TUPLE[0]}.{PY_VER_TUPLE[1]}"

## Set directory for requirements.txt file output
REQUIREMENTS_OUTPUT_DIR: Path = Path("./requirements")
## Ensure REQUIREMENTS_OUTPUT_DIR path exists
if not REQUIREMENTS_OUTPUT_DIR.exists():
    try:
        REQUIREMENTS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        msg = Exception(
            f"Unable to create requirements export directory: '{REQUIREMENTS_OUTPUT_DIR}'. Details: {exc}"
        )
        print(msg)

        REQUIREMENTS_OUTPUT_DIR: Path = Path(".")


@nox.session(python=PY_VERSIONS, name="build-env", tags=["setup"])
@nox.parametrize("pdm_ver", [PDM_VER])
def setup_base_testenv(session: nox.Session, pdm_ver: str):
    log.info(f"Default Python: {DEFAULT_PYTHON}")
    session.install(f"pdm>={pdm_ver}")

    log.info("Installing dependencies with PDM")
    session.run("pdm", "sync")
    session.run("pdm", "install")


@nox.session(python=[DEFAULT_PYTHON], name="lint", tags=["quality"])
def run_linter(session: nox.Session):
    session.install("ruff", "black")

    for d in LINT_PATHS:
        if not Path(d).exists():
            log.warning(f"Skipping lint path '{d}', could not find path")
            pass
        else:
            lint_path: Path = Path(d)
            log.info(f"Running ruff imports sort on '{d}'")
            session.run(
                "ruff",
                "check",
                "--select",
                "I",
                "--fix",
                lint_path,
            )

            log.info(f"Formatting '{d}' with Black")
            session.run(
                "black",
                lint_path,
            )

            # log.info(f"Running ruff checks on '{d}' with --fix")
            # session.run(
            #     "ruff",
            #     "check",
            #     "--config",
            #     "ruff.ci.toml",
            #     lint_path,
            #     "--fix",
            # )


@nox.session(
    python=[DEFAULT_PYTHON], name="lint-prune-script", tags=["cleanup", "quality"]
)
def run_linter(session: nox.Session):
    session.install("ruff", "black")

    lint_path: Path = Path("git_prune.py")
    log.info(f"Running ruff imports sort on '{lint_path}'")
    session.run(
        "ruff",
        "check",
        "--select",
        "I",
        "--fix",
        lint_path,
    )

    log.info(f"Formatting '{lint_path}' with Black")
    session.run(
        "black",
        lint_path,
    )


@nox.session(python=[DEFAULT_PYTHON], name="export", tags=["requirements"])
@nox.parametrize("pdm_ver", [PDM_VER])
def export_requirements(session: nox.Session, pdm_ver: str):
    session.install(f"pdm>={pdm_ver}")

    log.info("Exporting production requirements")
    session.run(
        "pdm",
        "export",
        "--prod",
        # "--no-default",
        "-o",
        f"{REQUIREMENTS_OUTPUT_DIR}/requirements.txt",
        "--without-hashes",
    )

    log.info("Exporting development requirements")
    session.run(
        "pdm",
        "export",
        "-d",
        "--no-default",
        "-o",
        f"{REQUIREMENTS_OUTPUT_DIR}/requirements.dev.txt",
        "--without-hashes",
    )

    log.info("Exporting docs requirements")
    session.run(
        "pdm",
        "export",
        "-G",
        "docs",
        "--no-default",
        "-o",
        "docs/requirements.txt",
        "--without-hashes",
    )

    log.info("Exporting test requirements")
    session.run(
        "pdm",
        "export",
        "-G",
        "tests",
        "--no-default",
        "-o",
        f"{REQUIREMENTS_OUTPUT_DIR}/requirements.tests.txt",
        "--without-hashes",
    )

    # log.info("Exporting CI requirements")
    # session.run(
    #     "pdm",
    #     "export",
    #     "--group",
    #     "ci",
    #     "-o",
    #     f"{REQUIREMENTS_OUTPUT_DIR}/requirements.ci.txt",
    #     "--without-hashes",
    # )


@nox.session(python=PY_VERSIONS, name="tests", tags=["test", "quality"])
@nox.parametrize("pdm_ver", [PDM_VER])
def run_tests(session: nox.Session, pdm_ver: str):
    session.install("-r", f"{REQUIREMENTS_OUTPUT_DIR}/requirements.tests.txt")

    log.info("Running Pytest tests")
    session.run(
        "pdm",
        "run",
        "pytest",
        "-n",
        "auto",
        "--tb=native",
        "-v",
        "-rasXxfP",
    )


@nox.session(python=PY_VERSIONS, name="sqla-tests", tags=["test", "quality"])
@nox.parametrize("pdm_ver", [PDM_VER])
def run_sqla_tests(session: nox.Session, pdm_ver: str):
    session.install(f"pdm>={pdm_ver}")
    session.run("pdm", "install")

    log.info(f"Running SQLAlchemy Pytest tests")
    session.run(
        "pdm",
        "run",
        "pytest",
        "-n",
        "auto",
        "-v",
        "-rsXxfP",
        "tests/test_sqlalchemy_utils.py",
    )


@nox.session(python=[DEFAULT_PYTHON], name="docs", tags=["docs"])
@nox.parametrize("pdm_ver", [PDM_VER])
def build_docs(session: nox.Session, pdm_ver: str):
    session.install(f"pdm>={pdm_ver}")
    session.run("pdm", "install", "-d")

    log.info("Building docs with mkdocs")
    session.run("pdm", "run", "mkdocs", "build")


# @nox.session(python=[PY_VER_TUPLE], name="init-setup")
# def run_initial_setup(session: nox.Session):
#     if INIT_COPY_FILES is None:
#         print(f"INIT_COPY_FILES is empty. Skipping")
#         pass

#     else:

#         for pair_dict in INIT_COPY_FILES:
#             src = Path(pair_dict["src"])
#             dest = Path(pair_dict["dest"])
#             if not dest.exists():
#                 print(f"Copying {src} to {dest}")
#                 try:
#                     shutil.copy(src, dest)
#                 except Exception as exc:
#                     msg = Exception(
#                         f"Unhandled exception copying file from '{src}' to '{dest}'. Details: {exc}"
#                     )
#                     print(f"[ERROR] {msg}")


@nox.session(python=[DEFAULT_PYTHON], name="vulture-check", tags=["quality"])
def run_vulture_check(session: nox.Session):
    session.install(f"vulture")

    log.info("Checking for dead code with vulture")
    try:
        session.run("vulture", "src/red_utils", "--min-confidence", "100")
    except Exception as exc:
        log.info(
            f"\nNote: For some reason, this always 'fails' with exit code 3. Vulture still works when running in a Nox session, it seems this error can be ignored."
        )


@nox.session(python=[DEFAULT_PYTHON], name="bandit-check", tags=["quality"])
def run_bandit_check(session: nox.Session):
    session.install(f"bandit")

    log.info("Checking code security with bandit")
    try:
        session.run("bandit", "-r", "src/red_utils")
    except Exception as exc:
        log.warning(
            f"\nNote: For some reason, this always 'fails' with exit code 1. Bandit still works when running in a Nox session, it seems this error can be ignored."
        )


@nox.session(python=[DEFAULT_PYTHON], name="bandit-baseline", tags=["quality"])
def run_bandit_baseline(session: nox.Session):
    session.install(f"bandit")

    log.info("Getting bandit baseline")
    try:
        session.run(
            "bandit", "-r", "src/red_utils", "-f", "json", "-o", "bandit_baseline.json"
        )
    except Exception as exc:
        log.warning(
            f"\nNote: For some reason, this always 'fails' with exit code 1. Bandit still works when running in a Nox session, it seems this error can be ignored."
        )


@nox.session(python=[DEFAULT_PYTHON], name="detect-secrets", tags=["quality"])
def scan_for_secrets(session: nox.Session):
    session.install("detect-secrets")

    log.info("Scanning project for secrets")
    session.run("detect-secrets", "scan")


@nox.session(python=[DEFAULT_PYTHON], name="radon-code-complexity", tags=["quality"])
def radon_code_complexity(session: nox.Session):
    session.install("radon")

    log.info("Getting code complexity score")
    session.run(
        "radon",
        "cc",
        "src/red_utils",
        "-s",
        "-a",
        "--total-average",
        "-nc",
        # "-j",
        # "-O",
        # "radon_complexity_results.json",
    )


@nox.session(python=[DEFAULT_PYTHON], name="radon-raw", tags=["quality"])
def radon_raw(session: nox.Session):
    session.install("radon")

    log.info("Running radon raw scan")
    session.run(
        "radon",
        "raw",
        "src/red_utils",
        "-s",
        # "-j",
        # "-O",
        # "radon_raw_results.json"
    )


@nox.session(python=[DEFAULT_PYTHON], name="radon-maintainability", tags=["quality"])
def radon_maintainability(session: nox.Session):
    session.install("radon")

    log.info("Running radon maintainability scan")
    session.run(
        "radon",
        "mi",
        "src/red_utils",
        "-n",
        "C",
        "-x",
        "F",
        "-s",
        # "-j",
        # "-O",
        # "radon_maitinability_results.json",
    )


@nox.session(python=[DEFAULT_PYTHON], name="radon-halstead", tags=["quality"])
def radon_halstead(session: nox.Session):
    session.install("radon")

    log.info("Running radon Halstead metrics scan")
    session.run(
        "radon",
        "hal",
        "src",
        "red_utils",
        "-f",
        # "-j",
        # "-O",
        # "radon_halstead_results.json",
    )


@nox.session(python=[DEFAULT_PYTHON], name="xenon", tags=["quality"])
def xenon_scan(session: nox.Session):
    session.install("xenon")

    log.info("Scanning complexity with xenon")
    try:
        session.run("xenon", "-b", "B", "-m", "C", "-a", "C", "src/red_utils")
    except Exception as exc:
        log.warning(
            f"\nNote: For some reason, this always 'fails' with exit code 1. Xenon still works when running in a Nox session, it seems this error can be ignored."
        )
