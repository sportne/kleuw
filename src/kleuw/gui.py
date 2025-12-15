"""Tkinter-based GUI scaffolding for Kleuw.

The UI shell created here satisfies the layout requirements described in
``spec/kleuw_ui.md`` while intentionally keeping callbacks as placeholders.
Future tasks will wire these controls into the backing project model.
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

from kleuw.hashing import compute_region_hash
from kleuw.io import load_project, save_project
from kleuw.model import HashDigest, LineSpan, Link, LinkType, RegionHash, Target
from kleuw.project import Project
from kleuw.staleness import LinkStalenessResult, check_link_staleness

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
        filedialog_module: Any | None = None,
        enable_tooltips: bool = True,
        project: Project | None = None,
    ) -> None:
        self._tk = tk_module
        self._ttk = ttk_module
        self._messagebox: Any = messagebox_module
        self._filedialog = (
            filedialog_module if filedialog_module is not None else filedialog
        )
        self._tooltips_enabled = enable_tooltips
        self._project = project if project is not None else Project()
        self._project_path: str | None = None
        self._is_dirty = False
        self.root = root if root is not None else self._tk.Tk(className="kleuw")
        self.root.title("Kleuw")
        self.root.geometry("1200x800")
        self.root.minsize(1024, 640)

        self.project_path_var = self._tk.StringVar(value="No project loaded")
        self.dirty_var = self._tk.StringVar(value="● Clean")
        self.selection_var = self._tk.StringVar(value="Selections: Left —, Right —")
        self.staleness_var = self._tk.StringVar(value="Staleness: Unknown")
        self._files: list[str] = []
        self._file_listbox: Any | None = None
        self._left_viewer: ViewerPane | None = None
        self._right_viewer: ViewerPane | None = None
        self.relationship_var = self._tk.StringVar(value="")
        self._create_link_button: Any | None = None
        self._links_tree: Any | None = None
        self._show_all_links_button: Any | None = None
        self._staleness_results: dict[str, LinkStalenessResult] = {}
        self._staleness_summary: tuple[int, int] | None = None
        self._show_stale_only = False

        style = self._ttk.Style()
        style.configure("Tooltip.TLabel", background="#ffffe0")

        self._build_menu_bar()
        self._build_toolbar()
        self._build_layout()
        self._build_status_bar()
        self._bind_shortcuts()
        self._update_selection_summary()

    def _get_action_callback(self, action: str) -> Callable[[], None]:
        callbacks: dict[str, Callable[[], None]] = {
            "New": self._new_project,
            "New Project": self._new_project,
            "Open": self._open_project,
            "Open Project": self._open_project,
            "Save": self._save_project,
            "Save As": self._save_project_as,
            "Check Staleness": self._run_staleness_check,
            "Create Link": self._create_link,
        }
        return callbacks.get(action, partial(self._placeholder_action, action))

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
                    command=self._get_action_callback(item.label),
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
                command=self._get_action_callback(button.label),
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
        self._file_listbox = self._tk.Listbox(parent, height=15, activestyle="dotbox")
        self._file_listbox.pack(fill=self._tk.BOTH, expand=True, pady=(4, 8))
        self._file_listbox.bind(
            "<Double-Button-1>",
            lambda _event: self._open_selection_in_viewer("left"),
        )
        self._file_listbox.bind(
            "<Shift-Double-Button-1>",
            lambda _event: self._open_selection_in_viewer("right"),
        )

        button_frame = self._ttk.Frame(parent)
        button_frame.pack(fill=self._tk.X)
        button_actions: dict[str, Callable[[], None]] = {
            "Add File": self._add_files,
            "Remove File": self._remove_selected_files,
            "Open Left": lambda: self._open_selection_in_viewer("left"),
            "Open Right": lambda: self._open_selection_in_viewer("right"),
        }
        for button in FILE_PANEL_BUTTONS:
            widget = self._ttk.Button(
                button_frame,
                text=button.label,
                command=button_actions.get(
                    button.label, partial(self._placeholder_action, button.label)
                ),
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

        self._left_viewer = self._build_viewer(viewer_split, "Left Viewer")
        self._right_viewer = self._build_viewer(viewer_split, "Right Viewer")

        controls = self._ttk.Frame(parent, padding=(0, 8, 0, 0))
        controls.pack(fill=self._tk.X)
        self._ttk.Label(controls, text="Relationship Type:").pack(side=self._tk.LEFT)
        relationship_combo = self._ttk.Combobox(
            controls,
            textvariable=self.relationship_var,
            values=self._relationship_values,
            state="readonly",
            width=20,
        )
        relationship_combo.pack(side=self._tk.LEFT, padx=8)
        relationship_combo.bind(
            "<<ComboboxSelected>>",
            lambda _event: self._update_create_button_state(),
        )
        swap_btn = self._ttk.Button(
            controls,
            text="↔",
            width=3,
            command=self._swap_viewer_files,
        )
        swap_btn.pack(side=self._tk.LEFT, padx=4)
        self._create_link_button = self._ttk.Button(
            controls,
            text="Create Link",
            command=self._create_link,
        )
        self._create_link_button.pack(side=self._tk.LEFT, padx=4)
        self._ttk.Label(
            controls,
            textvariable=self.selection_var,
            foreground="#555555",
        ).pack(side=self._tk.RIGHT)
        self._update_create_button_state()

    def _build_viewer(self, parent: Any, label: str) -> ViewerPane:
        frame = self._ttk.Frame(parent)
        parent.add(frame, weight=1)
        label_var = self._tk.StringVar(value=f"{label} — No file loaded")
        self._ttk.Label(frame, textvariable=label_var).pack(anchor=self._tk.W)

        body = self._ttk.Frame(frame)
        body.pack(fill=self._tk.BOTH, expand=True)
        line_numbers = self._tk.Text(
            body,
            wrap=self._tk.NONE,
            state=self._tk.DISABLED,
            width=4,
            takefocus=False,
            font="TkFixedFont",
            background="#f4f4f4",
            relief=self._tk.SUNKEN,
            borderwidth=0,
        )
        line_numbers.pack(side=self._tk.LEFT, fill=self._tk.Y)
        text = self._tk.Text(
            body,
            wrap=self._tk.NONE,
            height=20,
            font="TkFixedFont",
        )
        text.pack(fill=self._tk.BOTH, expand=True, side=self._tk.LEFT)
        self._make_text_readonly(text)
        y_scroll = self._ttk.Scrollbar(body, orient=self._tk.VERTICAL)
        y_scroll.pack(side=self._tk.RIGHT, fill=self._tk.Y)
        x_scroll = self._ttk.Scrollbar(body, orient=self._tk.HORIZONTAL)
        x_scroll.pack(fill=self._tk.X, side=self._tk.BOTTOM)

        def _on_vertical_scroll(*args: str) -> None:
            text.yview(*args)
            line_numbers.yview(*args)

        def _on_text_scroll(*args: str) -> None:
            y_scroll.set(*args)
            if args:
                line_numbers.yview_moveto(args[0])

        y_scroll.configure(command=_on_vertical_scroll)
        text.configure(yscrollcommand=_on_text_scroll, xscrollcommand=x_scroll.set)
        line_numbers.configure(yscrollcommand=y_scroll.set)
        x_scroll.configure(command=text.xview)
        pane = ViewerPane(
            label_prefix=label,
            label_var=label_var,
            text_widget=text,
            line_numbers_widget=line_numbers,
            y_scroll=y_scroll,
            x_scroll=x_scroll,
        )
        text.tag_configure(LINE_SELECTION_TAG, background="#cfe8ff")
        text.bind(
            "<Button-1>",
            lambda event, pane=pane: self._handle_selection_start(pane, event),
        )
        text.bind(
            "<B1-Motion>",
            lambda event, pane=pane: self._handle_selection_drag(pane, event),
        )
        text.bind(
            "<ButtonRelease-1>",
            lambda event, pane=pane: self._handle_selection_end(pane, event),
        )
        return pane

    def _build_links_panel(self, parent: Any) -> None:
        self._ttk.Label(parent, text="Links", font=("TkDefaultFont", 10, "bold")).pack(
            anchor=self._tk.W
        )
        columns = LINK_COLUMNS
        tree = self._ttk.Treeview(parent, columns=columns, show="headings", height=6)
        for column in columns:
            tree.heading(column, text=column)
            tree.column(column, width=120, anchor=self._tk.W)
        tree.tag_configure("stale", background="#fff9c4")
        y_scroll = self._ttk.Scrollbar(
            parent, orient=self._tk.VERTICAL, command=tree.yview
        )
        tree.configure(yscrollcommand=y_scroll.set)
        tree.pack(fill=self._tk.BOTH, expand=True, side=self._tk.LEFT, pady=(4, 0))
        y_scroll.pack(fill=self._tk.Y, side=self._tk.RIGHT, pady=(4, 0))
        tree.bind(
            "<Double-1>",
            lambda _event: self._navigate_to_selected_link(),
        )
        tree.bind(
            "<Button-3>",
            lambda event: self._show_links_context_menu(event, tree),
        )
        self._links_tree = tree

        button_row = self._ttk.Frame(parent, padding=(0, 8, 0, 0))
        button_row.pack(fill=self._tk.X)
        self._ttk.Button(
            button_row,
            text="Edit Link",
            command=self._edit_selected_link,
        ).pack(side=self._tk.LEFT, padx=(0, 4))
        self._ttk.Button(
            button_row,
            text="Delete Link",
            command=self._delete_selected_links,
        ).pack(side=self._tk.LEFT)
        self._show_all_links_button = self._ttk.Button(
            button_row,
            text="Show All",
            command=self._clear_links_filter,
            state=self._tk.DISABLED,
        )
        self._show_all_links_button.pack(side=self._tk.LEFT, padx=(4, 0))
        self._refresh_links_panel()
        self._update_links_filter_button()

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

    # ------------------------------------------------------------------
    # Project IO
    # ------------------------------------------------------------------
    def _new_project(self) -> None:
        if self._confirm_discard_changes():
            self._project = Project()
            self._project_path = None
            self._reset_ui_state()

    def _open_project(self) -> None:
        if not self._confirm_discard_changes():
            return
        path = self._filedialog.askopenfilename(
            title="Open Kleuw Project",
            filetypes=(("Kleuw JSON", "*.json"), ("All files", "*.*")),
        )
        if not path:
            return
        try:
            project = load_project(path)
        except (OSError, ValueError) as exc:
            self._messagebox.showerror(
                title="Kleuw", message=f"Could not open '{path}':\n{exc}"
            )
            return
        self._project = project
        self._project_path = path
        self._reset_ui_state()
        self.project_path_var.set(path)
        self._files = [
            str(entry.get("path", ""))
            for entry in self._project.files
            if isinstance(entry, dict) and "path" in entry
        ]
        if self._file_listbox:
            for file_path in self._files:
                self._file_listbox.insert(self._tk.END, file_path)

    def _save_project(self) -> None:
        if self._project_path is None:
            self._save_project_as()
            return
        try:
            save_project(self._project_path, self._project)
            self._set_dirty(False)
        except (OSError, ValueError) as exc:
            self._messagebox.showerror(
                title="Kleuw",
                message=f"Could not save '{self._project_path}':\n{exc}",
            )

    def _save_project_as(self) -> None:
        path = self._filedialog.asksaveasfilename(
            title="Save Kleuw Project As",
            filetypes=(("Kleuw JSON", "*.json"), ("All files", "*.*")),
            defaultextension=".json",
        )
        if not path:
            return
        try:
            save_project(path, self._project)
            self._project_path = path
            self.project_path_var.set(path)
            self._set_dirty(False)
        except (OSError, ValueError) as exc:
            self._messagebox.showerror(
                title="Kleuw", message=f"Could not save '{path}':\n{exc}"
            )

    def _confirm_discard_changes(self) -> bool:
        if not self._is_dirty:
            return True
        return bool(
            self._messagebox.askyesno(
                title="Kleuw",
                message="You have unsaved changes. Are you sure you want to discard them?",
            )
        )

    def _reset_ui_state(self) -> None:
        self.project_path_var.set("New Project (unsaved)")
        self._set_dirty(False)
        self._staleness_results = {}
        self._staleness_summary = None
        self._show_stale_only = False
        self._files.clear()
        if self._file_listbox:
            self._file_listbox.delete(0, self._tk.END)
        if self._left_viewer:
            self._apply_viewer_content(self._left_viewer, "", "")
        if self._right_viewer:
            self._apply_viewer_content(self._right_viewer, "", "")
        self._clear_all_selections()
        self._refresh_links_panel()
        self._update_staleness_label()
        self._update_links_filter_button()

    # ------------------------------------------------------------------
    # Staleness helpers
    # ------------------------------------------------------------------
    def _run_staleness_check(self) -> None:
        try:
            annotated = self._annotate_links_with_staleness()
        except ValueError as exc:
            self._messagebox.showerror(title="Kleuw", message=str(exc))
            return

        results = {result.link_id: result for _entry, result in annotated}
        stale_count = sum(1 for _entry, result in annotated if result.stale)
        self._staleness_results = results
        self._staleness_summary = (len(annotated), stale_count)
        self._set_stale_filter(False, force=True)
        self._show_staleness_dialog(total=len(annotated), stale=stale_count)

    def _annotate_links_with_staleness(
        self,
    ) -> list[tuple[dict[str, Any], LinkStalenessResult]]:
        file_lookup = self._build_file_lookup()
        annotated: list[tuple[dict[str, Any], LinkStalenessResult]] = []
        for entry in self._project.links:
            if not isinstance(entry, Mapping):
                continue
            entry_dict = entry
            try:
                link = _link_from_mapping(entry_dict)
            except ValueError as exc:
                identifier = entry_dict.get("id")
                label = f"link '{identifier}'" if identifier else "link"
                raise ValueError(f"Invalid {label}: {exc}") from exc
            result = check_link_staleness(link, file_lookup=file_lookup)
            annotated.append((entry_dict, result))
        return annotated

    def _build_file_lookup(self) -> dict[str, Mapping[str, Any]]:
        lookup: dict[str, Mapping[str, Any]] = {}
        for entry in self._project.files:
            if not isinstance(entry, Mapping):
                continue
            file_id = entry.get("id")
            if isinstance(file_id, str) and file_id:
                lookup[file_id] = entry
        return lookup

    def _show_staleness_dialog(self, *, total: int, stale: int) -> None:
        dialog = self._tk.Toplevel(self.root)
        dialog.title("Staleness Check Complete")
        dialog.transient(self.root)
        dialog.grab_set()
        content = self._ttk.Frame(dialog, padding=12)
        content.pack(fill=self._tk.BOTH, expand=True)
        self._ttk.Label(
            content, text="Staleness Check Complete", font=("TkDefaultFont", 11, "bold")
        ).pack(anchor=self._tk.W)
        self._ttk.Label(content, text=f"Total Links: {total}").pack(
            anchor=self._tk.W, pady=(8, 0)
        )
        self._ttk.Label(content, text=f"Stale Links: {stale}").pack(anchor=self._tk.W)

        button_row = self._ttk.Frame(content, padding=(0, 12, 0, 0))
        button_row.pack(anchor=self._tk.E, fill=self._tk.X)

        def _view() -> None:
            dialog.destroy()
            if stale:
                self._set_stale_filter(True)

        view_button = self._ttk.Button(
            button_row, text="View Stale Links", command=_view
        )
        view_button.pack(side=self._tk.LEFT, padx=(0, 4))
        close_button = self._ttk.Button(
            button_row, text="Close", command=dialog.destroy
        )
        close_button.pack(side=self._tk.LEFT)
        if stale == 0:
            view_button.configure(state=self._tk.DISABLED)

    def _set_stale_filter(self, enabled: bool, *, force: bool = False) -> None:
        if not force and self._show_stale_only == enabled:
            return
        self._show_stale_only = enabled
        self._refresh_links_panel()
        self._update_links_filter_button()
        self._update_staleness_label()

    def _clear_links_filter(self) -> None:
        self._set_stale_filter(False)

    def _update_links_filter_button(self) -> None:
        if self._show_all_links_button is None:
            return
        state = self._tk.NORMAL if self._show_stale_only else self._tk.DISABLED
        self._show_all_links_button.configure(state=state)

    def _update_staleness_label(self) -> None:
        if self._staleness_summary is None:
            text = "Staleness: Unknown"
        else:
            total, stale = self._staleness_summary
            text = f"Staleness: {stale} stale of {total}"
            if self._show_stale_only:
                text += " (filtered)"
        self.staleness_var.set(text)

    @property
    def _relationship_values(self) -> tuple[str, ...]:
        return tuple(link_type.value for link_type in LinkType)

    # ------------------------------------------------------------------
    # Viewer interaction helpers
    # ------------------------------------------------------------------
    def _make_text_readonly(self, widget: Any) -> None:
        widget.bind("<Key>", lambda _event: "break")
        widget.bind("<<Paste>>", lambda _event: "break")
        widget.bind("<<Cut>>", lambda _event: "break")
        widget.bind("<<Clear>>", lambda _event: "break")

    def _handle_selection_start(self, viewer: ViewerPane, event: Any) -> str:
        line = self._line_from_event(viewer, event)
        if line is None:
            return "break"
        viewer.selection_anchor = line
        self._set_viewer_selection(viewer, line, line)
        return "break"

    def _handle_selection_drag(self, viewer: ViewerPane, event: Any) -> str:
        line = self._line_from_event(viewer, event)
        if line is None:
            return "break"
        anchor = (
            viewer.selection_anchor if viewer.selection_anchor is not None else line
        )
        self._set_viewer_selection(viewer, anchor, line)
        return "break"

    def _handle_selection_end(self, viewer: ViewerPane, event: Any) -> str:
        line = self._line_from_event(viewer, event)
        if line is not None:
            anchor = (
                viewer.selection_anchor if viewer.selection_anchor is not None else line
            )
            self._set_viewer_selection(viewer, anchor, line)
        viewer.selection_anchor = None
        return "break"

    def _line_from_event(self, viewer: ViewerPane, event: Any) -> int | None:
        widget = viewer.text_widget
        try:
            index = widget.index(f"@{getattr(event, 'x', 0)},{getattr(event, 'y', 0)}")
        except Exception:  # pragma: no cover - depends on Tk
            return None
        return self._line_from_index(index, viewer)

    def _line_from_index(self, index: Any, viewer: ViewerPane) -> int | None:
        try:
            line_text = str(index).split(".")[0]
            line_number = int(line_text)
        except (ValueError, AttributeError):  # pragma: no cover - defensive
            return None
        return self._clamp_line(viewer, line_number)

    def _clamp_line(self, viewer: ViewerPane, line_number: int) -> int:
        if viewer.line_count <= 0:
            return 1
        return max(1, min(line_number, viewer.line_count))

    def _set_viewer_selection(
        self,
        viewer: ViewerPane,
        start_line: int | None,
        end_line: int | None = None,
    ) -> None:
        if start_line is None:
            self._clear_viewer_selection(viewer)
            return
        if end_line is None:
            end_line = start_line
        start = self._clamp_line(viewer, start_line)
        end = self._clamp_line(viewer, end_line)
        if end < start:
            start, end = end, start
        viewer.selection_start = start
        viewer.selection_end = end
        viewer.text_widget.tag_remove(LINE_SELECTION_TAG, "1.0", self._tk.END)
        line_limit = viewer.line_count if viewer.line_count > 0 else 1
        end_index = min(end + 1, line_limit + 1)
        viewer.text_widget.tag_add(
            LINE_SELECTION_TAG,
            f"{start}.0",
            f"{end_index}.0",
        )
        self._update_selection_summary()

    def _clear_viewer_selection(self, viewer: ViewerPane) -> None:
        viewer.selection_start = None
        viewer.selection_end = None
        viewer.selection_anchor = None
        viewer.text_widget.tag_remove(LINE_SELECTION_TAG, "1.0", self._tk.END)
        self._update_selection_summary()

    def _clear_all_selections(self) -> None:
        if self._left_viewer is not None:
            self._clear_viewer_selection(self._left_viewer)
        if self._right_viewer is not None:
            self._clear_viewer_selection(self._right_viewer)

    def _update_selection_summary(self) -> None:
        left_text = self._format_selection(self._left_viewer)
        right_text = self._format_selection(self._right_viewer)
        self.selection_var.set(f"Selections: Left {left_text}, Right {right_text}")

    def _format_selection(self, viewer: ViewerPane | None) -> str:
        if viewer is None or viewer.selection_start is None:
            return "—"
        end = (
            viewer.selection_end
            if viewer.selection_end is not None
            else viewer.selection_start
        )
        if end == viewer.selection_start:
            return f"L{viewer.selection_start}"
        return f"L{viewer.selection_start}–L{end}"

    def _update_viewer_label(self, viewer: ViewerPane) -> None:
        suffix = viewer.file_path if viewer.file_path else "No file loaded"
        viewer.label_var.set(f"{viewer.label_prefix} — {suffix}")

    # ------------------------------------------------------------------
    # Files panel helpers
    # ------------------------------------------------------------------

    def _bind_shortcuts(self) -> None:
        placeholder_bindings = {
            "<Control-n>": "New Project",
            "<Control-o>": "Open Project",
            "<Control-s>": "Save",
            "<Control-k>": "Check Staleness",
            "<Control-plus>": "Increase Font Size",
            "<Control-minus>": "Decrease Font Size",
            "<Alt-w>": "Toggle Line Wrapping",
        }
        for sequence, action in placeholder_bindings.items():
            self.root.bind(sequence, self._shortcut_handler(action))
        self.root.bind("<Control-Return>", self._invoke_create_link_shortcut)
        self.root.bind("<Escape>", self._clear_selections_shortcut)

    def _shortcut_handler(self, action: str) -> Callable[[Any], str]:
        def handler(event: Any) -> str:
            callback = self._get_action_callback(action)
            callback()
            return "break"

        return handler

    def _invoke_create_link_shortcut(self, _event: Any) -> str:
        self._create_link()
        return "break"

    def _clear_selections_shortcut(self, _event: Any) -> str:
        self._clear_all_selections()
        return "break"

    def _placeholder_action(self, action: str) -> None:
        self._messagebox.showinfo(
            title="Kleuw", message=f"{action} is not implemented yet."
        )

    # ------------------------------------------------------------------
    # Files panel helpers
    # ------------------------------------------------------------------
    def _add_files(self) -> None:
        if not hasattr(self._filedialog, "askopenfilenames"):
            self._messagebox.showinfo(
                title="Kleuw", message="File dialogs are unavailable."
            )
            return
        selection = self._filedialog.askopenfilenames(
            title="Add files to Kleuw project"
        )
        if not selection:
            return
        for raw_path in selection:
            expanded = Path(raw_path).expanduser()
            try:
                normalized = str(expanded.resolve())
            except OSError:
                normalized = str(expanded)
            if normalized and normalized not in self._files:
                self._files.append(normalized)
                if self._file_listbox is not None:
                    self._file_listbox.insert(self._tk.END, normalized)

    def _remove_selected_files(self) -> None:
        if self._file_listbox is None:
            return
        indices = sorted(
            (int(i) for i in self._file_listbox.curselection()), reverse=True
        )
        for index in indices:
            if 0 <= index < len(self._files):
                self._files.pop(index)
                self._file_listbox.delete(index)

    def _open_selection_in_viewer(self, side: str) -> None:
        viewer = self._get_viewer(side)
        if viewer is None:
            return
        if self._file_listbox is None:
            self._messagebox.showinfo(
                title="Kleuw", message="No files are available to open."
            )
            return
        selection = self._file_listbox.curselection()
        if not selection:
            self._messagebox.showinfo(
                title="Kleuw", message="Select a file to open in the viewer."
            )
            return
        index = int(selection[0])
        if not (0 <= index < len(self._files)):
            return
        path = self._files[index]
        self._load_file_into_viewer(viewer, path)

    def _get_viewer(self, side: str) -> ViewerPane | None:
        if side == "left":
            return self._left_viewer
        if side == "right":
            return self._right_viewer
        return None

    def _load_file_into_viewer(self, viewer: ViewerPane, path: str) -> None:
        try:
            content = self._normalize_newlines(
                Path(path).read_text(encoding="utf-8", errors="replace")
            )
        except OSError as exc:
            self._messagebox.showerror(
                title="Kleuw", message=f"Could not open '{path}': {exc}".strip()
            )
            return
        self._apply_viewer_content(viewer, path, content)
        self.selection_var.set(f"Loaded {Path(path).name} into {viewer.label_prefix}")

    def _apply_viewer_content(
        self, viewer: ViewerPane, path: str, content: str
    ) -> None:
        line_count = self._line_count(content)
        line_numbers = "\n".join(str(index) for index in range(1, line_count + 1))
        width = max(4, len(str(line_count)) + 1)
        self._set_text(viewer.text_widget, content)
        self._set_text(viewer.line_numbers_widget, line_numbers)
        viewer.line_numbers_widget.configure(width=width)
        viewer.text_widget.yview_moveto(0.0)
        viewer.text_widget.xview_moveto(0.0)
        viewer.line_numbers_widget.yview_moveto(0.0)
        viewer.file_path = path
        viewer.line_count = line_count
        self._update_viewer_label(viewer)
        self._clear_viewer_selection(viewer)
        self._update_create_button_state()

    def _set_text(self, widget: Any, text_value: str) -> None:
        widget.configure(state=self._tk.NORMAL)
        widget.delete("1.0", self._tk.END)
        if text_value:
            widget.insert("1.0", text_value)
        widget.configure(state=self._tk.NORMAL)

    def _normalize_newlines(self, content: str) -> str:
        normalized = content.replace("\r\n", "\n").replace("\r", "\n")
        return normalized

    def _line_count(self, content: str) -> int:
        if not content:
            return 1
        return content.count("\n") + 1

    # ------------------------------------------------------------------
    # Link workspace helpers
    # ------------------------------------------------------------------
    def _viewer_has_file(self, viewer: ViewerPane | None) -> bool:
        return bool(viewer and viewer.file_path)

    def _update_create_button_state(self) -> None:
        if self._create_link_button is None:
            return
        enabled = (
            self._viewer_has_file(self._left_viewer)
            and self._viewer_has_file(self._right_viewer)
            and bool(self.relationship_var.get())
        )
        state = self._tk.NORMAL if enabled else self._tk.DISABLED
        self._create_link_button.configure(state=state)

    def _swap_viewer_files(self) -> None:
        if self._left_viewer is None or self._right_viewer is None:
            return
        left_snapshot = self._capture_viewer_snapshot(self._left_viewer)
        right_snapshot = self._capture_viewer_snapshot(self._right_viewer)
        self._restore_viewer_snapshot(self._left_viewer, right_snapshot)
        self._restore_viewer_snapshot(self._right_viewer, left_snapshot)
        self._update_create_button_state()

    def _capture_viewer_snapshot(self, viewer: ViewerPane) -> dict[str, Any]:
        selection: tuple[int, int] | None = None
        if viewer.selection_start is not None:
            end = (
                viewer.selection_end
                if viewer.selection_end is not None
                else viewer.selection_start
            )
            selection = (viewer.selection_start, end)
        return {
            "file_path": viewer.file_path,
            "line_count": viewer.line_count,
            "text": self._get_widget_text(viewer.text_widget),
            "line_numbers": self._get_widget_text(viewer.line_numbers_widget),
            "selection": selection,
        }

    def _restore_viewer_snapshot(
        self, viewer: ViewerPane, snapshot: dict[str, Any]
    ) -> None:
        self._set_text(viewer.text_widget, snapshot.get("text", ""))
        self._set_text(viewer.line_numbers_widget, snapshot.get("line_numbers", ""))
        viewer.line_count = int(snapshot.get("line_count", 0))
        viewer.file_path = snapshot.get("file_path")
        self._update_viewer_label(viewer)
        selection = snapshot.get("selection")
        if selection is None:
            self._clear_viewer_selection(viewer)
        else:
            self._set_viewer_selection(viewer, selection[0], selection[1])

    def _get_widget_text(self, widget: Any) -> str:
        try:
            text = widget.get("1.0", self._tk.END)
        except Exception:  # pragma: no cover - defensive
            return ""
        return str(text).rstrip("\n")

    def _line_span_for_viewer(self, viewer: ViewerPane) -> LineSpan | None:
        if viewer.selection_start is None:
            return None
        end = (
            viewer.selection_end
            if viewer.selection_end is not None
            else viewer.selection_start
        )
        return LineSpan(start=viewer.selection_start, end=end)

    def _build_target_for_viewer(self, viewer: ViewerPane, *, label: str) -> Target:
        if viewer.file_path is None:
            raise ValueError(f"No file is loaded in the {label} viewer.")
        lines = self._line_span_for_viewer(viewer)
        region_hash = self._compute_target_hash(
            viewer.file_path, lines=lines, label=label
        )
        file_entry = self._project.find_file_by_path(viewer.file_path)
        if file_entry is not None:
            file_id = file_entry.get("id") if isinstance(file_entry, dict) else None
            if file_id:
                return Target(
                    file_id=str(file_id), lines=lines, region_hash=region_hash
                )
        return Target(path=viewer.file_path, lines=lines, region_hash=region_hash)

    def _compute_target_hash(
        self, path: str, *, lines: LineSpan | None, label: str
    ) -> RegionHash:
        start_line = lines.start if lines is not None else None
        end_line = lines.end if lines is not None else None
        try:
            return compute_region_hash(path, start_line=start_line, end_line=end_line)
        except FileNotFoundError as exc:
            raise ValueError(
                f"{label.capitalize()} file '{path}' does not exist."
            ) from exc
        except UnicodeDecodeError as exc:
            raise ValueError(
                f"{label.capitalize()} file '{path}' is not valid UTF-8."
            ) from exc
        except ValueError as exc:
            raise ValueError(f"Invalid line range for {label}: {exc}") from exc

    def _generate_link_id(self) -> str:
        counter = 1
        while True:
            candidate = f"link-{counter}"
            if not self._project.find_link_by_id(candidate):
                return candidate
            counter += 1

    def _create_link(self) -> None:
        if not (self._left_viewer and self._right_viewer):
            return
        if not self._viewer_has_file(self._left_viewer) or not self._viewer_has_file(
            self._right_viewer
        ):
            self._messagebox.showinfo(
                title="Kleuw",
                message="Load files into both viewers before creating a link.",
            )
            return
        relationship_value = self.relationship_var.get().strip()
        if not relationship_value:
            self._messagebox.showinfo(
                title="Kleuw",
                message="Select a relationship type before creating a link.",
            )
            return
        try:
            link_type = LinkType(relationship_value)
        except ValueError:
            self._messagebox.showerror(
                title="Kleuw",
                message=f"Unknown relationship type '{relationship_value}'.",
            )
            return
        try:
            src_target = self._build_target_for_viewer(
                self._left_viewer, label="source"
            )
            dst_target = self._build_target_for_viewer(
                self._right_viewer, label="destination"
            )
        except ValueError as exc:
            self._messagebox.showerror(title="Kleuw", message=str(exc))
            return
        link = Link(
            id=self._generate_link_id(),
            type=link_type,
            src=src_target,
            dst=dst_target,
        )
        try:
            self._project.add_link(link)
        except ValueError as exc:
            self._messagebox.showerror(title="Kleuw", message=str(exc))
            return
        self._set_dirty(True)
        self._refresh_links_panel(selected_id=link.id)
        self._update_create_button_state()

    # ------------------------------------------------------------------
    # Links panel helpers
    # ------------------------------------------------------------------
    def _refresh_links_panel(self, *, selected_id: str | None = None) -> None:
        if self._links_tree is None:
            return
        tree = self._links_tree
        for item in tree.get_children():
            tree.delete(item)
        for entry in self._project.links:
            if not isinstance(entry, Mapping):
                continue
            link_id = str(entry.get("id", ""))
            result = self._staleness_results.get(link_id)
            is_stale = bool(result and result.stale)
            if self._show_stale_only and not is_stale:
                continue
            if result is None:
                stale_text = "Unknown"
            else:
                stale_text = "Yes" if result.stale else "No"
            values = (
                link_id,
                str(entry.get("type", "")),
                self._format_target(entry.get("src", {})),
                self._format_target(entry.get("dst", {})),
                stale_text,
                ", ".join(entry.get("tags", [])) if entry.get("tags") else "",
                "Yes" if entry.get("note") else "",
            )
            tags = ("stale",) if is_stale else ()
            tree.insert("", self._tk.END, iid=link_id, values=values, tags=tags)
        if selected_id is not None:
            try:
                tree.selection_set(selected_id)
            except Exception:  # pragma: no cover - Tk fallback
                pass

    def _format_target(self, target: Any) -> str:
        if not isinstance(target, dict):
            return ""
        path = self._resolve_target_path(target)
        if path is None:
            return ""
        lines = target.get("lines")
        if isinstance(lines, dict):
            start = lines.get("start")
            end = lines.get("end")
            if isinstance(start, int):
                if isinstance(end, int) and end != start:
                    return f"{path} L{start}–L{end}"
                return f"{path} L{start}"
        return path

    def _show_links_context_menu(self, event: Any, tree: Any) -> None:
        menu = self._tk.Menu(self.root, tearoff=False)
        menu.add_command(label="Open", command=self._navigate_to_selected_link)
        menu.add_command(label="Edit", command=self._edit_selected_link)
        menu.add_command(label="Delete", command=self._delete_selected_links)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:  # pragma: no cover - Tk handles grab release
            menu.grab_release()

    def _navigate_to_selected_link(self) -> None:
        if self._links_tree is None:
            return
        selection = self._links_tree.selection()
        if not selection:
            return
        self._navigate_to_link_id(str(selection[0]))

    def _navigate_to_link_id(self, link_id: str) -> None:
        link_entry = self._project.find_link_by_id(link_id)
        if link_entry is None:
            self._messagebox.showerror(
                title="Kleuw", message=f"Link '{link_id}' no longer exists."
            )
            return
        if self._left_viewer is None or self._right_viewer is None:
            return
        self.relationship_var.set(str(link_entry.get("type", "")))
        try:
            self._load_target_into_viewer(
                self._left_viewer, link_entry.get("src", {}), label="Left"
            )
            self._load_target_into_viewer(
                self._right_viewer, link_entry.get("dst", {}), label="Right"
            )
        except ValueError as exc:
            self._messagebox.showerror(title="Kleuw", message=str(exc))

    def _load_target_into_viewer(
        self,
        viewer: ViewerPane,
        target: Any,
        *,
        label: str,
    ) -> None:
        if not isinstance(target, dict):
            raise ValueError("Link target is malformed.")
        path = self._resolve_target_path(target)
        if path is None:
            raise ValueError("Link target references an unknown file.")
        self._load_file_into_viewer(viewer, path)
        lines = target.get("lines")
        start_line: int | None = None
        end_line: int | None = None
        if isinstance(lines, dict) and "start" in lines:
            start_value = lines.get("start")
            end_value = lines.get("end")
            start_line = start_value if isinstance(start_value, int) else None
            if isinstance(end_value, int):
                end_line = end_value
        self._set_viewer_selection(viewer, start_line, end_line)
        if start_line is not None:
            self._scroll_viewer_to_line(viewer, start_line)
        else:
            self.selection_var.set(f"Loaded {Path(path).name} into {label}")

    def _scroll_viewer_to_line(self, viewer: ViewerPane, line_number: int) -> None:
        line = self._clamp_line(viewer, line_number)
        try:
            viewer.text_widget.see(f"{line}.0")
        except Exception:  # pragma: no cover - depends on Tk
            return

    def _resolve_target_path(self, target: dict[str, Any]) -> str | None:
        path_value = target.get("path")
        if isinstance(path_value, str) and path_value:
            return path_value
        file_id = target.get("file_id")
        if isinstance(file_id, str) and file_id:
            file_entry = self._project.find_file_by_id(file_id)
            if isinstance(file_entry, dict):
                candidate = file_entry.get("path")
                if isinstance(candidate, str) and candidate:
                    return candidate
        return None

    def _delete_selected_links(self) -> None:
        if self._links_tree is None:
            return
        selection = self._links_tree.selection()
        removed = False
        for item_id in selection:
            link_id = str(item_id)
            if self._project.remove_link(link_id) is not None:
                removed = True
        if removed:
            self._set_dirty(True)
            self._refresh_links_panel()

    def _edit_selected_link(self) -> None:
        if self._links_tree is None:
            return
        selection = self._links_tree.selection()
        if not selection:
            return
        link_id = str(selection[0])
        link_entry = self._project.find_link_by_id(link_id)
        if link_entry is None:
            self._messagebox.showerror(
                title="Kleuw", message=f"Link '{link_id}' no longer exists."
            )
            return
        self._open_edit_dialog(link_entry)

    def _open_edit_dialog(self, link_entry: dict[str, Any]) -> None:
        dialog = self._tk.Toplevel(self.root)
        dialog.title(f"Edit Link {link_entry.get('id', '')}")
        dialog.transient(self.root)
        dialog.grab_set()
        content = self._ttk.Frame(dialog, padding=12)
        content.pack(fill=self._tk.BOTH, expand=True)

        type_var = self._tk.StringVar(value=str(link_entry.get("type", "")))
        tags_var = self._tk.StringVar(value=", ".join(link_entry.get("tags", [])))
        note_var = self._tk.StringVar(value=str(link_entry.get("note", "")))

        self._ttk.Label(content, text="Relationship Type:").grid(
            row=0, column=0, sticky=self._tk.W
        )
        type_combo = self._ttk.Combobox(
            content,
            textvariable=type_var,
            values=self._relationship_values,
            state="readonly",
            width=25,
        )
        type_combo.grid(row=0, column=1, sticky=self._tk.W, pady=4)

        self._ttk.Label(content, text="Tags:").grid(row=1, column=0, sticky=self._tk.W)
        tags_entry = self._ttk.Entry(content, textvariable=tags_var, width=40)
        tags_entry.grid(row=1, column=1, sticky=self._tk.W, pady=4)

        self._ttk.Label(content, text="Note:").grid(row=2, column=0, sticky=self._tk.W)
        note_entry = self._ttk.Entry(content, textvariable=note_var, width=40)
        note_entry.grid(row=2, column=1, sticky=self._tk.W, pady=4)

        button_row = self._ttk.Frame(content)
        button_row.grid(row=3, column=0, columnspan=2, pady=(8, 0))

        def _save() -> None:
            self._apply_link_edit(
                str(link_entry.get("id", "")),
                type_value=type_var.get(),
                tags_text=tags_var.get(),
                note_text=note_var.get(),
            )
            dialog.destroy()

        def _cancel() -> None:
            dialog.destroy()

        self._ttk.Button(button_row, text="Save", command=_save).pack(
            side=self._tk.LEFT, padx=(0, 4)
        )
        self._ttk.Button(button_row, text="Cancel", command=_cancel).pack(
            side=self._tk.LEFT
        )
        tags_entry.focus_set()

    def _apply_link_edit(
        self,
        link_id: str,
        *,
        type_value: str,
        tags_text: str,
        note_text: str,
    ) -> None:
        link_entry = self._project.find_link_by_id(link_id)
        if link_entry is None:
            self._messagebox.showerror(
                title="Kleuw", message=f"Link '{link_id}' no longer exists."
            )
            return
        try:
            normalized_type = LinkType(type_value).value
        except ValueError:
            self._messagebox.showerror(
                title="Kleuw", message=f"Unknown relationship type '{type_value}'."
            )
            return
        link_entry["type"] = normalized_type
        tags = [tag.strip() for tag in tags_text.split(",") if tag.strip()]
        if tags:
            link_entry["tags"] = tags
        elif "tags" in link_entry:
            del link_entry["tags"]
        note = note_text.strip()
        if note:
            link_entry["note"] = note
        elif "note" in link_entry:
            del link_entry["note"]
        self._set_dirty(True)
        self._refresh_links_panel(selected_id=link_id)

    def _set_dirty(self, is_dirty: bool) -> None:
        self._is_dirty = is_dirty
        self.dirty_var.set("● Unsaved changes" if is_dirty else "● Clean")

    def run(self) -> None:
        """Start the Tkinter main loop."""

        self.root.mainloop()


def _link_from_mapping(entry: Mapping[str, Any]) -> Link:
    src_data = entry.get("src")
    dst_data = entry.get("dst")
    if not isinstance(src_data, Mapping) or not isinstance(dst_data, Mapping):
        raise ValueError("Links must define 'src' and 'dst' targets.")
    link_type = entry.get("type")
    if link_type is None:
        raise ValueError("Links must define a 'type'.")
    tags = entry.get("tags") or ()
    if isinstance(tags, str):
        tags_value: Sequence[str] = (tags,)
    else:
        try:
            tags_value = tuple(str(tag) for tag in tags)
        except TypeError as exc:  # pragma: no cover - defensive copy of CLI helper
            raise ValueError("Link tags must be iterable.") from exc

    directed = entry.get("directed")
    directed_value = True if directed is None else bool(directed)
    return Link(
        id=str(entry.get("id", "")),
        type=LinkType(link_type),
        src=_target_from_mapping(src_data, region_key="src_region_hash"),
        dst=_target_from_mapping(dst_data, region_key="dst_region_hash"),
        directed=directed_value,
        created=entry.get("created"),
        author=entry.get("author"),
        tags=tags_value,
        note=entry.get("note"),
    )


def _target_from_mapping(target: Mapping[str, Any], *, region_key: str) -> Target:
    file_id = target.get("file_id")
    path = target.get("path")
    lines = _line_span_from_mapping(target.get("lines"))
    hash_data = target.get(region_key) or target.get("region_hash")
    region_hash = _region_hash_from_mapping(hash_data) if hash_data else None
    return Target(file_id=file_id, path=path, lines=lines, region_hash=region_hash)


def _line_span_from_mapping(data: object | None) -> LineSpan | None:
    if data is None:
        return None
    if isinstance(data, LineSpan):
        return data
    if not isinstance(data, Mapping):
        raise ValueError("Line span must be a mapping.")
    start = data.get("start")
    end = data.get("end")
    if not isinstance(start, int):
        raise ValueError("Line span requires an integer 'start'.")
    if end is not None and not isinstance(end, int):
        raise ValueError("Line span 'end' must be an integer when provided.")
    return LineSpan(start=start, end=end)


def _region_hash_from_mapping(data: object) -> RegionHash:
    if isinstance(data, RegionHash):
        return data
    if isinstance(data, HashDigest):
        return RegionHash(algo=data.algo, value=data.value)
    if isinstance(data, Mapping):
        algo = data.get("algo")
        value = data.get("value")
        if isinstance(algo, str) and isinstance(value, str):
            return RegionHash(algo=algo, value=value)
    raise ValueError("Region hash must define 'algo' and 'value'.")


def launch() -> None:
    """Launch the Kleuw GUI."""

    KleuwGUI().run()


if __name__ == "__main__":  # pragma: no cover - manual entry point
    launch()
