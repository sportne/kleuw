"""Private data structures and constants for the Kleuw GUI.

This module is not part of the public API.
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Sequence
from dataclasses import dataclass
from tkinter import ttk
from typing import Any

__all__ = [
    "create_tooltip",
    "MenuItem",
    "ToolbarButton",
    "Tooltip",
    "ViewerPane",
    "FILE_PANEL_BUTTONS",
    "LINE_SELECTION_TAG",
    "LINK_COLUMNS",
    "MENU_DEFINITION",
    "TOOLBAR_BUTTONS",
    "_DEFAULT_FONT_SIZE",
    "_FONT_NAME",
    "_MAX_FONT_SIZE",
    "_MIN_FONT_SIZE",
    "_THEME_DEFAULT",
    "_THEME_HIGH_CONTRAST",
]


_FONT_NAME = "TkFixedFont"
_MIN_FONT_SIZE = 8
_MAX_FONT_SIZE = 24
_DEFAULT_FONT_SIZE = 10


_THEME_DEFAULT = {
    "bg": "#ffffff",
    "fg": "#000000",
    "select_bg": "#cfe8ff",
    "select_fg": "#000000",
    "disabled_fg": "#a0a0a0",
    "gutter_bg": "#f4f4f4",
    "stale_bg": "#fff9c4",
    "tooltip_bg": "#ffffe0",
}


_THEME_HIGH_CONTRAST = {
    "bg": "#000000",
    "fg": "#ffff00",
    "select_bg": "#00ffff",
    "select_fg": "#000000",
    "disabled_fg": "#808080",
    "gutter_bg": "#222222",
    "stale_bg": "#440000",
    "tooltip_bg": "#333333",
}


@dataclass(frozen=True, slots=True)
class MenuItem:
    """Menu entry description used to construct the menubar."""

    label: str | None
    tooltip: str | None


@dataclass(frozen=True, slots=True)
class ToolbarButton:
    """Toolbar button description."""

    label: str
    tooltip: str


@dataclass(slots=True)
class ViewerPane:
    """Container storing widgets and metadata for a text viewer."""

    label_prefix: str
    label_var: Any
    text_widget: Any
    line_numbers_widget: Any
    y_scroll: Any
    x_scroll: Any
    file_path: str | None = None
    line_count: int = 0
    selection_start: int | None = None
    selection_end: int | None = None
    selection_anchor: int | None = None


LINE_SELECTION_TAG = "line-selection"


MENU_DEFINITION: tuple[tuple[str, Sequence[MenuItem]], ...] = (
    (
        "File",
        (
            MenuItem("New Project", "Create a new Kleuw project."),
            MenuItem("Open Project", "Open an existing project."),
            MenuItem("Save", "Save the active project."),
            MenuItem("Save As", "Save the project to a new path."),
            MenuItem("Recent Projects", "Show the most recently opened projects."),
            MenuItem(None, None),
            MenuItem("Exit", "Quit Kleuw."),
        ),
    ),
    (
        "Edit",
        (
            MenuItem("Undo", "Undo the last change."),
            MenuItem("Redo", "Redo the previously undone change."),
            MenuItem("Preferences", "Open the preferences dialog."),
        ),
    ),
    (
        "View",
        (
            MenuItem("Toggle Files Panel", "Show or hide the files panel."),
            MenuItem("Toggle Links Panel", "Show or hide the links panel."),
            MenuItem("Increase Font Size", "Make the viewers' font larger."),
            MenuItem("Decrease Font Size", "Make the viewers' font smaller."),
            MenuItem("Toggle Line Wrapping", "Enable or disable line wrapping."),
            MenuItem(None, None),
            MenuItem("Toggle High Contrast", "Enable or disable high contrast mode."),
        ),
    ),
    (
        "Links",
        (
            MenuItem("Create Link", "Create a new relationship."),
            MenuItem("Edit Link", "Edit the selected link."),
            MenuItem("Delete Link", "Remove the selected link."),
            MenuItem("Check Staleness", "Check for stale relationships."),
            MenuItem("Recompute Hashes", "Recompute hashes for displayed files."),
        ),
    ),
    (
        "Tools",
        (
            MenuItem("Validate Project", "Validate the current project."),
            MenuItem("Export Summary", "Export a project summary."),
        ),
    ),
    (
        "Help",
        (
            MenuItem("About", "Show information about Kleuw."),
            MenuItem("Keyboard Shortcuts", "List available shortcuts."),
        ),
    ),
)


TOOLBAR_BUTTONS: tuple[ToolbarButton, ...] = (
    ToolbarButton("New", "Create a new Kleuw project."),
    ToolbarButton("Open", "Open an existing project."),
    ToolbarButton("Save", "Save the current project."),
    ToolbarButton("Add File", "Add a file to the project."),
    ToolbarButton("Check Staleness", "Recompute all link hashes."),
    ToolbarButton("Create Link", "Create a link from the current selections."),
)


FILE_PANEL_BUTTONS: tuple[ToolbarButton, ...] = (
    ToolbarButton("Add File", "Add a source file to the project."),
    ToolbarButton("Remove File", "Remove the selected file from the project."),
    ToolbarButton("Open Left", "Open the selected file in the left viewer."),
    ToolbarButton("Open Right", "Open the selected file in the right viewer."),
)


LINK_COLUMNS: tuple[str, ...] = (
    "ID",
    "Type",
    "Source",
    "Destination",
    "Stale?",
    "Tags",
    "Notes",
)


class Tooltip:
    """Simple tooltip helper for Tkinter widgets."""

    def __init__(self, widget: tk.Widget, text: str = "") -> None:
        self.widget = widget
        self.text = text
        self._tip: tk.Toplevel | None = None

    def set_text(self, text: str) -> None:
        """Update the tooltip text."""
        self.text = text

    def show(self, event: tk.Event[Any] | None = None) -> None:
        """Display the tooltip at the event's position."""
        if self._tip:
            self.hide()

        if not self.text:
            return

        x = self.widget.winfo_rootx() + 12
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        if event:
            x = event.x_root + 12
            y = event.y_root + 10

        self._tip = tk.Toplevel(self.widget)
        self._tip.wm_overrideredirect(True)
        self._tip.wm_geometry(f"+{x}+{y}")
        label = ttk.Label(
            self._tip,
            text=self.text,
            style="Tooltip.TLabel",
            padding=(6, 2),
        )
        label.pack()

    def hide(self, _event: tk.Event[Any] | None = None) -> None:
        """Hide the tooltip."""
        if self._tip:
            self._tip.destroy()
        self._tip = None


def create_tooltip(widget: tk.Widget, text: str) -> None:
    """Create and bind a simple static tooltip."""
    tooltip = Tooltip(widget, text)
    widget.bind("<Enter>", tooltip.show)
    widget.bind("<Leave>", tooltip.hide)
    widget.bind("<ButtonPress>", tooltip.hide)
