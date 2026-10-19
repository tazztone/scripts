"""Nautilus desktop integration components for media_toolbox."""

from __future__ import annotations

from typing import Any

from media_toolbox.nautilus.installer import (
    install_nautilus,
    status_nautilus,
    uninstall_nautilus,
)

__all__ = [
    "MediaToolboxExtension",
    "is_media_file",
    "install_nautilus",
    "uninstall_nautilus",
    "status_nautilus",
]


def __getattr__(name: str) -> Any:
    if name in ("MediaToolboxExtension", "is_media_file"):
        from media_toolbox.nautilus.extension import (
            MediaToolboxExtension,
            is_media_file,
        )

        if name == "MediaToolboxExtension":
            return MediaToolboxExtension
        return is_media_file
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
