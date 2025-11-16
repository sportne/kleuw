"""Tkinter-based GUI scaffolding for Kleuw.

The UI shell created here satisfies the layout requirements described in
``spec/kleuw_ui.md`` while intentionally keeping callbacks as placeholders.
Future tasks will wire these controls into the backing project model.
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from functools import partial
from tkinter import messagebox, ttk
from typing import Any

from kleuw.model import LinkType

__all__ = ["KleuwGUI", "launch"]


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
            MenuItem("Delete Link", "Delete the currently selected link."),
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

    def __init__(self, widget: tk.Widget, text: str) -> None:
        self.widget = widget
        self.text = text
        self._tip: tk.Toplevel | None = None
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)
        widget.bind("<ButtonPress>", self._hide)

    def _show(self, _event: tk.Event[Any] | None = None) -> None:
        if self._tip is not None:
            return
        x = self.widget.winfo_rootx() + 12
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
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

    def _hide(self, _event: tk.Event[Any] | None = None) -> None:
        if self._tip is not None:
            self._tip.destroy()
            self._tip = None


class KleuwGUI:
    """Tkinter GUI shell matching the Kleuw UI specification."""

    def __init__(
        self,
        root: Any | None = None,
        *,
        tk_module: Any = tk,
        ttk_module: Any = ttk,
        messagebox_module: Any = messagebox,
        enable_tooltips: bool = True,
    ) -> None:
        self._tk = tk_module
        self._ttk = ttk_module
        self._messagebox = messagebox_module
        self._tooltips_enabled = enable_tooltips
        self.root = root if root is not None else self._tk.Tk(className="kleuw")
        self.root.title("Kleuw")
        self.root.geometry("1200x800")
        self.root.minsize(1024, 640)

        self.project_path_var = self._tk.StringVar(value="No project loaded")
        self.dirty_var = self._tk.StringVar(value="● Clean")
        self.selection_var = self._tk.StringVar(value="Selections: Left —, Right —")
        self.staleness_var = self._tk.StringVar(value="Staleness: Unknown")

        style = self._ttk.Style()
        style.configure("Tooltip.TLabel", background="#ffffe0")

        self._build_menu_bar()
        self._build_toolbar()
        self._build_layout()
        self._build_status_bar()
        self._bind_shortcuts()

    def _build_menu_bar(self) -> None:
        menu_bar = self._tk.Menu(self.root)
        for menu_label, items in MENU_DEFINITION:
            menu = self._tk.Menu(menu_bar, tearoff=False)
            for item in items:
                if item.label is None:
                    menu.add_separator()
                    continue
                menu.add_command(
                    label=item.label,
                    command=partial(self._placeholder_action, item.label),
                )
            menu_bar.add_cascade(label=menu_label, menu=menu)
        self.root.config(menu=menu_bar)

    def _build_toolbar(self) -> None:
        toolbar = self._ttk.Frame(self.root, padding=(8, 4))
        toolbar.pack(fill=self._tk.X, side=self._tk.TOP)
        for button in TOOLBAR_BUTTONS:
            widget = self._ttk.Button(
                toolbar,
                text=button.label,
                command=partial(self._placeholder_action, button.label),
                padding=(8, 2),
            )
            widget.pack(side=self._tk.LEFT, padx=4)
            if self._tooltips_enabled:
                Tooltip(widget, button.tooltip)

    def _build_layout(self) -> None:
        container = self._ttk.PanedWindow(self.root, orient=self._tk.VERTICAL)
        container.pack(fill=self._tk.BOTH, expand=True)

        upper = self._ttk.PanedWindow(container, orient=self._tk.HORIZONTAL)
        container.add(upper, weight=3)

        files_frame = self._ttk.Frame(upper, padding=8)
        self._build_files_panel(files_frame)
        upper.add(files_frame, weight=1)

        workspace_frame = self._ttk.Frame(upper, padding=8)
        self._build_workspace(workspace_frame)
        upper.add(workspace_frame, weight=4)

        links_frame = self._ttk.Frame(container, padding=8)
        self._build_links_panel(links_frame)
        container.add(links_frame, weight=1)

    def _build_files_panel(self, parent: Any) -> None:
        self._ttk.Label(
            parent, text="Project Files", font=("TkDefaultFont", 10, "bold")
        ).pack(anchor=self._tk.W)
        listbox = self._tk.Listbox(parent, height=15, activestyle="dotbox")
        listbox.pack(fill=self._tk.BOTH, expand=True, pady=(4, 8))
        listbox.insert(self._tk.END, "(No files loaded)")
        listbox.bind(
            "<Double-Button-1>",
            lambda _event: self._placeholder_action("Open file in left viewer"),
        )
        listbox.bind(
            "<Shift-Double-Button-1>",
            lambda _event: self._placeholder_action("Open file in right viewer"),
        )

        button_frame = self._ttk.Frame(parent)
        button_frame.pack(fill=self._tk.X)
        for button in FILE_PANEL_BUTTONS:
            widget = self._ttk.Button(
                button_frame,
                text=button.label,
                command=partial(self._placeholder_action, button.label),
            )
            widget.pack(fill=self._tk.X, pady=2)
            if self._tooltips_enabled:
                Tooltip(widget, button.tooltip)

    def _build_workspace(self, parent: Any) -> None:
        self._ttk.Label(
            parent, text="Link Workspace", font=("TkDefaultFont", 10, "bold")
        ).pack(anchor=self._tk.W)
        viewer_split = self._ttk.PanedWindow(parent, orient=self._tk.HORIZONTAL)
        viewer_split.pack(fill=self._tk.BOTH, expand=True, pady=4)

        self._left_text = self._build_viewer(viewer_split, "Left Viewer")
        self._right_text = self._build_viewer(viewer_split, "Right Viewer")

        controls = self._ttk.Frame(parent, padding=(0, 8, 0, 0))
        controls.pack(fill=self._tk.X)
        self._ttk.Label(controls, text="Relationship Type:").pack(side=self._tk.LEFT)
        relationship_var = self._tk.StringVar(value="")
        relationship_combo = self._ttk.Combobox(
            controls,
            textvariable=relationship_var,
            values=self._relationship_values,
            state="readonly",
            width=20,
        )
        relationship_combo.pack(side=self._tk.LEFT, padx=8)
        swap_btn = self._ttk.Button(
            controls,
            text="↔",
            width=3,
            command=partial(self._placeholder_action, "Swap viewers"),
        )
        swap_btn.pack(side=self._tk.LEFT, padx=4)
        create_btn = self._ttk.Button(
            controls,
            text="Create Link",
            command=partial(self._placeholder_action, "Create Link"),
        )
        create_btn.pack(side=self._tk.LEFT, padx=4)
        self._ttk.Label(
            controls,
            textvariable=self.selection_var,
            foreground="#555555",
        ).pack(side=self._tk.RIGHT)

    def _build_viewer(self, parent: Any, label: str) -> Any:
        frame = self._ttk.Frame(parent)
        parent.add(frame, weight=1)
        self._ttk.Label(frame, text=label).pack(anchor=self._tk.W)
        text = self._tk.Text(
            frame,
            wrap=self._tk.NONE,
            height=20,
            state=self._tk.DISABLED,
            font="TkFixedFont",
        )
        text.pack(fill=self._tk.BOTH, expand=True, side=self._tk.LEFT)
        y_scroll = self._ttk.Scrollbar(
            frame, orient=self._tk.VERTICAL, command=text.yview
        )
        y_scroll.pack(side=self._tk.RIGHT, fill=self._tk.Y)
        text.configure(yscrollcommand=y_scroll.set)
        x_scroll = self._ttk.Scrollbar(
            frame, orient=self._tk.HORIZONTAL, command=text.xview
        )
        x_scroll.pack(fill=self._tk.X, side=self._tk.BOTTOM)
        text.configure(xscrollcommand=x_scroll.set)
        return text

    def _build_links_panel(self, parent: Any) -> None:
        self._ttk.Label(parent, text="Links", font=("TkDefaultFont", 10, "bold")).pack(
            anchor=self._tk.W
        )
        columns = LINK_COLUMNS
        tree = self._ttk.Treeview(parent, columns=columns, show="headings", height=6)
        for column in columns:
            tree.heading(column, text=column)
            tree.column(column, width=120, anchor=self._tk.W)
        y_scroll = self._ttk.Scrollbar(
            parent, orient=self._tk.VERTICAL, command=tree.yview
        )
        tree.configure(yscrollcommand=y_scroll.set)
        tree.pack(fill=self._tk.BOTH, expand=True, side=self._tk.LEFT, pady=(4, 0))
        y_scroll.pack(fill=self._tk.Y, side=self._tk.RIGHT, pady=(4, 0))
        tree.insert(
            "",
            self._tk.END,
            values=("L-001", "implements", "src", "dst", "No", "", ""),
        )
        tree.bind(
            "<Double-1>",
            lambda _event: self._placeholder_action("Navigate to link"),
        )

    def _build_status_bar(self) -> None:
        bar = self._ttk.Frame(self.root, relief=self._tk.SUNKEN, padding=(8, 4))
        bar.pack(fill=self._tk.X, side=self._tk.BOTTOM)
        self._ttk.Label(
            bar, textvariable=self.project_path_var, anchor=self._tk.W
        ).pack(side=self._tk.LEFT)
        self._ttk.Separator(bar, orient=self._tk.VERTICAL).pack(
            side=self._tk.LEFT, fill=self._tk.Y, padx=6
        )
        self._ttk.Label(bar, textvariable=self.dirty_var).pack(side=self._tk.LEFT)
        self._ttk.Separator(bar, orient=self._tk.VERTICAL).pack(
            side=self._tk.LEFT, fill=self._tk.Y, padx=6
        )
        self._ttk.Label(bar, textvariable=self.selection_var).pack(side=self._tk.LEFT)
        self._ttk.Separator(bar, orient=self._tk.VERTICAL).pack(
            side=self._tk.LEFT, fill=self._tk.Y, padx=6
        )
        self._ttk.Label(bar, textvariable=self.staleness_var).pack(side=self._tk.LEFT)

    @property
    def _relationship_values(self) -> tuple[str, ...]:
        return tuple(link_type.value for link_type in LinkType)

    def _bind_shortcuts(self) -> None:
        bindings = {
            "<Control-n>": "New Project",
            "<Control-o>": "Open Project",
            "<Control-s>": "Save",
            "<Control-Return>": "Create Link",
            "<Control-k>": "Check Staleness",
            "<Control-plus>": "Increase Font Size",
            "<Control-minus>": "Decrease Font Size",
            "<Alt-w>": "Toggle Line Wrapping",
            "<Escape>": "Clear selections",
        }
        for sequence, action in bindings.items():
            self.root.bind(sequence, self._shortcut_handler(action))

    def _shortcut_handler(self, action: str) -> Callable[[Any], str]:
        def handler(event: Any) -> str:
            self._placeholder_action(action)
            return "break"

        return handler

    def _placeholder_action(self, action: str) -> None:
        self.selection_var.set(f"Action requested: {action}")
        self._messagebox.showinfo(
            title="Kleuw", message=f"{action} is not implemented yet."
        )

    def run(self) -> None:
        """Start the Tkinter main loop."""

        self.root.mainloop()


def launch() -> None:
    """Launch the Kleuw GUI."""

    KleuwGUI().run()


if __name__ == "__main__":  # pragma: no cover - manual entry point
    launch()
