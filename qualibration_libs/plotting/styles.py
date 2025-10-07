from __future__ import annotations

from contextlib import contextmanager
from typing import Dict, Tuple, Optional, Iterable

from .config import PlotTheme

_PALETTES: Dict[str, Tuple[str, ...]] = {
    "qualibrate": PlotTheme().colorway,
    "deep": (
        "#4c72b0", "#dd8452", "#55a868", "#c44e52", "#8172b2", "#937860", "#da8bc3", "#8c8c8c", "#ccb974", "#64b5cd"),
    "muted": (
        "#4878d0", "#ee854a", "#6acc64", "#d65f5f", "#b47cc7", "#82c6e2", "#d5bb67", "#8c8c8c", "#ff9da6", "#9d755d"),
}


def set_theme(
    theme: Optional[PlotTheme] = None, *,
    palette: Optional[str | Iterable[str]] = None,
    rc: Optional[dict] = None
) -> None:
    global CURRENT_THEME, CURRENT_PALETTE, CURRENT_RC
    if theme is not None:
        CURRENT_THEME = theme
    if palette is not None:
        if isinstance(palette, str):
            CURRENT_PALETTE = _PALETTES.get(palette, PlotTheme().colorway)
        else:
            CURRENT_PALETTE = tuple(palette)
    if rc is not None:
        CURRENT_RC.values.update(rc)


def set_palette(palette: str | Iterable[str]) -> None:
    global CURRENT_PALETTE
    if isinstance(palette, str):
        CURRENT_PALETTE = _PALETTES.get(palette, PlotTheme().colorway)
    else:
        CURRENT_PALETTE = tuple(palette)


@contextmanager
def theme_context(
    theme: Optional[PlotTheme] = None, *,
    palette: Optional[str | Iterable[str]] = None,
    rc: Optional[dict] = None
):
    global CURRENT_THEME, CURRENT_PALETTE, CURRENT_RC
    orig_theme = CURRENT_THEME
    orig_palette = CURRENT_PALETTE
    orig_rc = dict(CURRENT_RC.values)
    try:
        set_theme(theme, palette=palette, rc=rc)
        yield
    finally:
        CURRENT_THEME = orig_theme
        CURRENT_PALETTE = orig_palette
        CURRENT_RC.values.clear()
        CURRENT_RC.values.update(orig_rc)
