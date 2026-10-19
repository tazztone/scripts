"""
Main execution router for the media_toolbox package.

Behavior:
1. If command-line arguments are provided, delegates immediately to media_toolbox.cli.
2. If no arguments are provided:
   - If a graphical display environment is available (DISPLAY or WAYLAND_DISPLAY),
     lazily imports and runs the Libadwaita/GTK4 desktop user interface (media_toolbox.ui.app).
   - If in a headless environment, prints the CLI help message.

INVARIANT: Strict zero top-level GUI imports. UI is loaded only conditionally and lazily.
"""

from __future__ import annotations

import importlib
import os
import sys


def main() -> int:
    """Route package execution between CLI and UI."""
    argv = sys.argv[1:]

    # Path 1: User specified CLI arguments or flags -> execute CLI directly
    if argv:
        from media_toolbox.cli import main as cli_main

        return cli_main(argv)

    # Path 2: No arguments supplied -> check for graphical display environment
    has_display = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    if has_display:
        try:
            ui_module = importlib.import_module("media_toolbox.ui.app")
            return ui_module.main()
        except (ImportError, ModuleNotFoundError) as err:
            # Desktop UI not installed or not yet implemented
            sys.stderr.write(
                f"Graphical display detected, but desktop UI could not be loaded ({err}).\n"
                "Falling back to CLI interface.\n\n"
            )
            from media_toolbox.cli import main as cli_main

            try:
                return cli_main(["--help"])
            except SystemExit as exc:
                return exc.code if isinstance(exc.code, int) else 0

    # Path 3: Headless environment with no arguments -> display CLI help
    from media_toolbox.cli import main as cli_main

    try:
        return cli_main(["--help"])
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 0


if __name__ == "__main__":
    sys.exit(main())
