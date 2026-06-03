"""Re-exports command modules for CLI registration."""

from noidea.commands import init, keys, reconcile, status, suggest, test, update
from noidea.commands.keys import keys_app

__all__ = [
    "init",
    "keys",
    "keys_app",
    "reconcile",
    "status",
    "suggest",
    "test",
    "update",
]
