from __future__ import annotations

from .local import clean_local_app

from cyclopts import App

clean_app = App(
    name="clean",
    help="Run cleanup operations, like deleting local branches that have been merged/removed from the remote.",
)

clean_app.command(clean_local_app)
