"""Patchwork: patch FileMaker files from code, with Claris FMUpgradeTool."""

__version__ = "0.1.0"


class PatchworkError(Exception):
    """An error the user can fix. The CLI prints it without a traceback."""
