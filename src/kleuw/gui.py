"""Tkinter-based GUI scaffolding for Kleuw.

The UI shell created here satisfies the layout requirements described in
``spec/kleuw_ui.md`` while intentionally keeping callbacks as placeholders.
Future tasks will wire these controls into the backing project model.
"""

from __future__ import annotations

import io
import tkinter as tk
from collections.abc import Callable, Mapping, Sequence
from functools import partial
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, TextIO

from kleuw.commands import (
    CommandHistory,
    CreateLinkCommand,
    DeleteLinkCommand,
    UpdateLinkCommand,
)
from kleuw.gui_parts import (
    _DEFAULT_FONT_SIZE,
    _FONT_NAME,
    _MAX_FONT_SIZE,
    _MIN_FONT_SIZE,
    _THEME_DEFAULT,
    _THEME_HIGH_CONTRAST,
    FILE_PANEL_BUTTONS,
    LINE_SELECTION_TAG,
    LINK_COLUMNS,
    MENU_DEFINITION,
    TOOLBAR_BUTTONS,
    Tooltip,
    ViewerPane,
    create_tooltip,
)
from kleuw.hashing import compute_region_hash
from kleuw.io import load_project, save_project
from kleuw.model import HashDigest, LineSpan, Link, LinkType, RegionHash, Target
from kleuw.project import Project
from kleuw.schema import validate_project
from kleuw.staleness import LinkStalenessResult, check_link_staleness

__all__ = ["KleuwGUI", "launch"]


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
        self._command_history = CommandHistory()
        self._font_size = _DEFAULT_FONT_SIZE
        self._line_wrapping_enabled = False
        self._high_contrast_enabled = False
        self.root = root if root is not None else self._tk.Tk(className="kleuw")
        self.root.title("Kleuw")
        self.root.geometry("1200x800")
        self.root.minsize(1024, 640)
        self.root.protocol("WM_DELETE_WINDOW", self._exit_app)

        self.project_path_var = self._tk.StringVar(value="No project loaded")
        self.dirty_var = self._tk.StringVar(value="● Clean")
        self.selection_var = self._tk.StringVar(value="Selections: Left —, Right —")
        self.staleness_var = self._tk.StringVar(value="Staleness: Unknown")
        self._files: list[str] = []
        self._file_listbox: Any | None = None
        self._files_frame: Any | None = None
        self._links_frame: Any | None = None
        self._main_container: Any | None = None
        self._upper_paned_window: Any | None = None
        self._left_viewer: ViewerPane | None = None
        self._right_viewer: ViewerPane | None = None
        self.relationship_var = self._tk.StringVar(value="")
        self._create_link_button: Any | None = None
        self._links_tree: Any | None = None
        self._show_all_links_button: Any | None = None
        self._staleness_results: dict[str, LinkStalenessResult] = {}
        self._staleness_summary: tuple[int, int] | None = None
        self._show_stale_only = False
        self._link_tooltip: Tooltip | None = None
        self._recent_projects: list[str] = []
        self._recent_projects_menu: Any | None = None

        self._apply_theme()

        self._build_menu_bar()
        self._build_toolbar()
        self._build_layout()
        self._build_status_bar()
        self._bind_shortcuts()
        self._update_selection_summary()
        self._update_recent_projects_menu()

    def _get_action_callback(self, action: str) -> Callable[[], None]:
        callbacks: dict[str, Callable[[], None]] = {
            "New": self._new_project,
            "New Project": self._new_project,
            "Open": self._open_project,
            "Open Project": self._open_project,
            "Save": self._save_project,
            "Save As": self._save_project_as,
            "Exit": self._exit_app,
            "Add File": self._add_files,
            "Check Staleness": self._run_staleness_check,
            "Create Link": self._create_link,
            "Undo": self._undo,
            "Redo": self._redo,
            "Edit Link": self._edit_selected_link,
            "Delete Link": self._delete_selected_links,
            "Preferences": self._open_preferences_dialog,
            "Toggle Files Panel": self._toggle_files_panel,
            "Toggle Links Panel": self._toggle_links_panel,
            "Increase Font Size": self._increase_font_size,
            "Decrease Font Size": self._decrease_font_size,
            "Toggle Line Wrapping": self._toggle_line_wrapping,
            "Toggle High Contrast": self._toggle_high_contrast,
            "Recompute Hashes": self._recompute_hashes,
            "Validate Project": self._validate_project,
            "Export Summary": self._export_summary,
            "About": self._show_about_dialog,
            "Keyboard Shortcuts": self._show_shortcuts_dialog,
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
                if item.label == "Recent Projects":
                    self._recent_projects_menu = self._tk.Menu(menu, tearoff=False)
                    menu.add_cascade(label=item.label, menu=self._recent_projects_menu)
                else:
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
                create_tooltip(widget, button.tooltip)

    def _build_layout(self) -> None:
        container = self._ttk.PanedWindow(self.root, orient=self._tk.VERTICAL)
        container.pack(fill=self._tk.BOTH, expand=True)
        self._main_container = container

        upper = self._ttk.PanedWindow(container, orient=self._tk.HORIZONTAL)
        container.add(upper, weight=3)
        self._upper_paned_window = upper

        files_frame = self._ttk.Frame(upper, padding=8)
        self._build_files_panel(files_frame)
        upper.add(files_frame, weight=1)
        self._files_frame = files_frame

        workspace_frame = self._ttk.Frame(upper, padding=8)
        self._build_workspace(workspace_frame)
        upper.add(workspace_frame, weight=4)

        links_frame = self._ttk.Frame(container, padding=8)
        self._build_links_panel(links_frame)
        container.add(links_frame, weight=1)
        self._links_frame = links_frame

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
                create_tooltip(widget, button.tooltip)

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
            font=(_FONT_NAME, self._font_size),
            background="#f4f4f4",
            relief=self._tk.SUNKEN,
            borderwidth=0,
        )
        line_numbers.pack(side=self._tk.LEFT, fill=self._tk.Y)
        text = self._tk.Text(
            body,
            wrap=self._tk.WORD if self._line_wrapping_enabled else self._tk.NONE,
            height=20,
            font=(_FONT_NAME, self._font_size),
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
        if self._tooltips_enabled:
            self._link_tooltip = Tooltip(tree)
            tree.bind("<Motion>", self._show_link_tooltip)
            tree.bind("<Leave>", self._hide_link_tooltip)

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

    def _show_link_tooltip(self, event: tk.Event[Any]) -> None:
        if self._links_tree is None or self._link_tooltip is None:
            return
        row_id = self._links_tree.identify_row(event.y)

        result = self._staleness_results.get(row_id) if row_id else None
        if result and result.stale:
            changed = []
            if result.src.stale:
                changed.append("source")
            if result.dst.stale:
                changed.append("destination")
            tooltip_text = f"Changed: {', '.join(changed)}"
            self._link_tooltip.set_text(tooltip_text)
            self._link_tooltip.show(event)
        else:
            self._link_tooltip.hide()

    def _hide_link_tooltip(self, _event: tk.Event[Any] | None = None) -> None:
        if self._link_tooltip:
            self._link_tooltip.hide()

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
        if path:
            self._load_project_from_path(path)

    def _open_recent_project(self, path: str) -> None:
        """Open a project from the recent projects list."""
        if self._confirm_discard_changes():
            self._load_project_from_path(path)

    def _load_project_from_path(self, path: str) -> None:
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
        self._add_to_recent_projects(path)

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

    def _recompute_hashes(self) -> None:
        """Recompute region hashes for all links in the project."""
        if not self._project.links:
            self._messagebox.showinfo(title="Kleuw", message="No links to recompute.")
            return

        if not self._messagebox.askyesno(
            title="Kleuw",
            message=(
                "This will recompute hashes for all links and mark the project as "
                "unsaved. Continue?"
            ),
        ):
            return

        updated_count = 0
        errors: list[str] = []

        for link_entry in self._project.links:
            if not isinstance(link_entry, Mapping):
                continue

            link_id = str(link_entry.get("id", ""))
            if not link_id:
                continue

            updates: dict[str, Any] = {}
            try:
                src_target_data = link_entry.get("src", {})
                new_src_hash = self._recompute_target_hash(src_target_data, "source")
                if new_src_hash:
                    new_src = dict(src_target_data)
                    new_src["src_region_hash"] = new_src_hash.to_dict()
                    if "region_hash" in new_src:
                        del new_src["region_hash"]
                    updates["src"] = new_src

                dst_target_data = link_entry.get("dst", {})
                new_dst_hash = self._recompute_target_hash(
                    dst_target_data, "destination"
                )
                if new_dst_hash:
                    new_dst = dict(dst_target_data)
                    new_dst["dst_region_hash"] = new_dst_hash.to_dict()
                    if "region_hash" in new_dst:
                        del new_dst["region_hash"]
                    updates["dst"] = new_dst
            except ValueError as exc:
                errors.append(f"Link '{link_id}': {exc}")
                continue

            if updates:
                command = UpdateLinkCommand(self._project, link_id, updates=updates)
                self._command_history.execute(command)
                updated_count += 1

        summary = f"Successfully recomputed hashes for {updated_count} link(s)."
        if errors:
            summary += "\n\nThe following errors occurred:\n" + "\n".join(errors)
        self._messagebox.showinfo(title="Kleuw", message=summary)

        if updated_count > 0:
            self._set_dirty(True)
            self._staleness_results.clear()
            self._staleness_summary = None
            self._update_staleness_label()
            self._refresh_links_panel()

    def _recompute_target_hash(self, target_data: Any, label: str) -> RegionHash | None:
        if not isinstance(target_data, Mapping):
            return None

        path = self._resolve_target_path(target_data)
        if path is None:
            raise ValueError(f"Could not resolve file path for {label} target.")

        lines_data = target_data.get("lines")
        lines = _line_span_from_mapping(lines_data) if lines_data is not None else None
        start_line = lines.start if lines is not None else None
        end_line = lines.end if lines is not None else None

        try:
            return compute_region_hash(path, start_line=start_line, end_line=end_line)
        except (FileNotFoundError, UnicodeDecodeError, ValueError) as exc:
            raise ValueError(
                f"Could not compute hash for {label} ('{path}'): {exc}"
            ) from exc

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

    def _add_to_recent_projects(self, path: str) -> None:
        """Add a path to the recent projects list and update the menu."""
        if path in self._recent_projects:
            self._recent_projects.remove(path)
        self._recent_projects.insert(0, path)
        if len(self._recent_projects) > 10:
            self._recent_projects = self._recent_projects[:10]
        self._update_recent_projects_menu()

    def _update_recent_projects_menu(self) -> None:
        """Populate the 'Recent Projects' menu."""
        if self._recent_projects_menu is None:
            return
        menu = self._recent_projects_menu
        menu.delete(0, self._tk.END)
        if not self._recent_projects:
            menu.add_command(label="No recent projects", state=self._tk.DISABLED)
        else:
            for path in self._recent_projects:
                menu.add_command(
                    label=path,
                    command=partial(self._open_recent_project, path),
                )

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
            "<Control-Shift-S>": "Save As",
            "<Control-z>": "Undo",
            "<Control-y>": "Redo",
            "<Control-Shift-Z>": "Redo",
            "<Delete>": "Delete Link",
            "<F2>": "Edit Link",
            "<Control-k>": "Check Staleness",
            "<Control-Shift-C>": "Recompute Hashes",
            "<Control-Shift-V>": "Validate Project",
            "<Control-e>": "Export Summary",
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

    def _exit_app(self) -> None:
        if self._confirm_discard_changes():
            self.root.destroy()

    def _open_preferences_dialog(self) -> None:
        """Open the preferences dialog."""
        dialog = self._tk.Toplevel(self.root)
        dialog.title("Preferences")
        dialog.transient(self.root)
        dialog.grab_set()

        content = self._ttk.Frame(dialog, padding=12)
        content.pack(fill=self._tk.BOTH, expand=True)

        font_size_var = self._tk.IntVar(value=self._font_size)
        line_wrapping_var = self._tk.BooleanVar(value=self._line_wrapping_enabled)

        # Font Size Setting
        self._ttk.Label(content, text="Font Size:").grid(
            row=0, column=0, sticky=self._tk.W, pady=(0, 4)
        )
        font_size_spinbox = self._ttk.Spinbox(
            content,
            from_=_MIN_FONT_SIZE,
            to=_MAX_FONT_SIZE,
            textvariable=font_size_var,
            width=5,
        )
        font_size_spinbox.grid(row=0, column=1, sticky=self._tk.W, pady=(0, 4))

        # Line Wrapping Setting
        line_wrapping_check = self._ttk.Checkbutton(
            content, text="Enable Line Wrapping", variable=line_wrapping_var
        )
        line_wrapping_check.grid(
            row=1, column=0, columnspan=2, sticky=self._tk.W, pady=(0, 12)
        )

        button_row = self._ttk.Frame(content)
        button_row.grid(row=2, column=0, columnspan=2, sticky=self._tk.E)

        def _apply() -> None:
            self._font_size = font_size_var.get()
            self._line_wrapping_enabled = line_wrapping_var.get()
            self._update_font()
            self._apply_line_wrapping()

        def _save() -> None:
            _apply()
            dialog.destroy()

        def _cancel() -> None:
            dialog.destroy()

        save_button = self._ttk.Button(button_row, text="Save", command=_save)
        save_button.pack(side=self._tk.LEFT, padx=(0, 4))
        cancel_button = self._ttk.Button(button_row, text="Cancel", command=_cancel)
        cancel_button.pack(side=self._tk.LEFT, padx=(0, 4))
        apply_button = self._ttk.Button(button_row, text="Apply", command=_apply)
        apply_button.pack(side=self._tk.LEFT)

        save_button.focus_set()

    def _show_about_dialog(self) -> None:
        """Show the 'About' dialog."""
        dialog = self._tk.Toplevel(self.root)
        dialog.title("About Kleuw")
        dialog.transient(self.root)
        dialog.grab_set()

        content = self._ttk.Frame(dialog, padding=12)
        content.pack(fill=self._tk.BOTH, expand=True)

        self._ttk.Label(content, text="Kleuw", font=("TkDefaultFont", 12, "bold")).pack(
            anchor=self._tk.W, pady=(0, 4)
        )
        self._ttk.Label(
            content, text="A tool for managing semantic file relationships."
        ).pack(anchor=self._tk.W)
        self._ttk.Label(content, text="Version: 0.1.0 (pre-release)").pack(
            anchor=self._tk.W, pady=(0, 12)
        )

        button_row = self._ttk.Frame(content)
        button_row.pack(fill=self._tk.X, anchor=self._tk.E)

        ok_button = self._ttk.Button(button_row, text="OK", command=dialog.destroy)
        ok_button.pack(side=self._tk.LEFT)
        ok_button.focus_set()

    def _show_shortcuts_dialog(self) -> None:
        """Display a dialog with a list of keyboard shortcuts."""
        shortcuts = {
            "New Project": "Ctrl+N",
            "Open Project": "Ctrl+O",
            "Save": "Ctrl+S",
            "Save As": "Ctrl+Shift+S",
            "Undo": "Ctrl+Z",
            "Redo": "Ctrl+Y / Ctrl+Shift+Z",
            "Delete Link": "Delete",
            "Edit Link": "F2",
            "Check Staleness": "Ctrl+K",
            "Recompute Hashes": "Ctrl+Shift+C",
            "Validate Project": "Ctrl+Shift+V",
            "Export Summary": "Ctrl+E",
            "Create Link": "Ctrl+Enter",
            "Increase Font Size": "Ctrl++",
            "Decrease Font Size": "Ctrl+-",
            "Toggle Line Wrapping": "Alt+W",
            "Clear Selections": "Esc",
        }

        dialog = self._tk.Toplevel(self.root)
        dialog.title("Keyboard Shortcuts")
        dialog.transient(self.root)
        dialog.grab_set()

        content = self._ttk.Frame(dialog, padding=12)
        content.pack(fill=self._tk.BOTH, expand=True)

        self._ttk.Label(
            content, text="Keyboard Shortcuts", font=("TkDefaultFont", 11, "bold")
        ).grid(row=0, column=0, columnspan=2, sticky=self._tk.W, pady=(0, 8))

        row = 1
        for action, shortcut in shortcuts.items():
            self._ttk.Label(content, text=action).grid(
                row=row, column=0, sticky=self._tk.W, padx=(0, 20)
            )
            self._ttk.Label(content, text=shortcut).grid(
                row=row, column=1, sticky=self._tk.W
            )
            row += 1

        button_row = self._ttk.Frame(content)
        button_row.grid(
            row=row, column=0, columnspan=2, pady=(12, 0), sticky=self._tk.E
        )

        ok_button = self._ttk.Button(button_row, text="OK", command=dialog.destroy)
        ok_button.pack()
        ok_button.focus_set()

    def _toggle_files_panel(self) -> None:
        """Show or hide the files panel."""
        if self._files_frame is None or self._upper_paned_window is None:
            return
        panes = self._upper_paned_window.panes()
        if self._files_frame.winfo_exists() and str(self._files_frame) in panes:
            self._upper_paned_window.remove(self._files_frame)
        else:
            self._upper_paned_window.insert(0, self._files_frame, weight=1)

    def _toggle_links_panel(self) -> None:
        """Show or hide the links panel."""
        if self._links_frame is None or self._main_container is None:
            return
        panes = self._main_container.panes()
        if self._links_frame.winfo_exists() and str(self._links_frame) in panes:
            self._main_container.remove(self._links_frame)
        else:
            self._main_container.add(self._links_frame, weight=1)

    def _increase_font_size(self) -> None:
        """Increase the font size in both viewers."""
        self._font_size = min(_MAX_FONT_SIZE, self._font_size + 1)
        self._update_font()

    def _decrease_font_size(self) -> None:
        """Decrease the font size in both viewers."""
        self._font_size = max(_MIN_FONT_SIZE, self._font_size - 1)
        self._update_font()

    def _apply_line_wrapping(self) -> None:
        """Apply the current line wrapping setting to both viewers."""
        wrap_mode = self._tk.WORD if self._line_wrapping_enabled else self._tk.NONE
        if self._left_viewer:
            self._left_viewer.text_widget.configure(wrap=wrap_mode)
        if self._right_viewer:
            self._right_viewer.text_widget.configure(wrap=wrap_mode)

    def _toggle_line_wrapping(self) -> None:
        """Toggle line wrapping in both viewers."""
        self._line_wrapping_enabled = not self._line_wrapping_enabled
        self._apply_line_wrapping()

    def _update_font(self) -> None:
        """Apply the current font size to both viewers."""
        font = (_FONT_NAME, self._font_size)
        if self._left_viewer:
            self._left_viewer.text_widget.configure(font=font)
            self._left_viewer.line_numbers_widget.configure(font=font)
        if self._right_viewer:
            self._right_viewer.text_widget.configure(font=font)
            self._right_viewer.line_numbers_widget.configure(font=font)

    def _toggle_high_contrast(self) -> None:
        """Toggle high contrast mode."""
        self._high_contrast_enabled = not self._high_contrast_enabled
        self._apply_theme()

    def _apply_theme(self) -> None:
        """Apply the current theme to all relevant widgets."""
        theme = _THEME_HIGH_CONTRAST if self._high_contrast_enabled else _THEME_DEFAULT
        style = self._ttk.Style()
        style.configure(
            "TFrame",
            background=theme["bg"],
            foreground=theme["fg"],
            fieldbackground=theme["bg"],
        )
        style.configure(
            "TLabel",
            background=theme["bg"],
            foreground=theme["fg"],
            fieldbackground=theme["bg"],
        )
        style.configure(
            "TButton",
            background=theme["bg"],
            foreground=theme["fg"],
            fieldbackground=theme["bg"],
            selectbackground=theme["select_bg"],
            selectforeground=theme["select_fg"],
        )
        style.configure(
            "Treeview",
            background=theme["bg"],
            foreground=theme["fg"],
            fieldbackground=theme["bg"],
            selectbackground=theme["select_bg"],
            selectforeground=theme["select_fg"],
        )
        style.map(
            "TButton",
            foreground=[("disabled", theme["disabled_fg"])],
        )
        style.configure(
            "Tooltip.TLabel", background=theme["tooltip_bg"], foreground=theme["fg"]
        )

        if self._links_tree:
            self._links_tree.tag_configure("stale", background=theme["stale_bg"])

        for viewer in (self._left_viewer, self._right_viewer):
            if viewer:
                viewer.text_widget.configure(
                    background=theme["bg"],
                    foreground=theme["fg"],
                    insertbackground=theme["fg"],
                )
                viewer.line_numbers_widget.configure(
                    background=theme["gutter_bg"],
                    foreground=theme["fg"],
                )
                viewer.text_widget.tag_configure(
                    LINE_SELECTION_TAG,
                    background=theme["select_bg"],
                    foreground=theme["select_fg"],
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
        widget.configure(state=self._tk.DISABLED)

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
        command = CreateLinkCommand(self._project, link.to_dict())
        try:
            self._command_history.execute(command)
        except ValueError as exc:
            self._messagebox.showerror(title="Kleuw", message=str(exc))
            return
        self._set_dirty(True)
        self._refresh_links_panel(selected_id=link.id)
        self._update_create_button_state()

    def _undo(self) -> None:
        if self._command_history.can_undo:
            self._command_history.undo()
            self._set_dirty(True)
            self._refresh_links_panel()

    def _redo(self) -> None:
        if self._command_history.can_redo:
            self._command_history.redo()
            self._set_dirty(True)
            self._refresh_links_panel()

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

    def _resolve_target_path(self, target: Mapping[str, Any]) -> str | None:
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

    def _delete_selected_links(self) -> None:
        if self._links_tree is None:
            return
        selection = self._links_tree.selection()
        if not selection:
            return

        removed_count = 0
        for item_id in selection:
            link_id = str(item_id)
            command = DeleteLinkCommand(self._project, link_id)
            result = self._command_history.execute(command)
            if result is not None:
                removed_count += 1

        if removed_count > 0:
            self._set_dirty(True)
            self._refresh_links_panel()

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
        try:
            link_type = LinkType(type_value).value
        except ValueError:
            self._messagebox.showerror(
                title="Kleuw", message=f"Unknown relationship type '{type_value}'."
            )
            return

        updates: dict[str, Any] = {"type": link_type}
        deletes: list[str] = []

        tags = [tag.strip() for tag in tags_text.split(",") if tag.strip()]
        if tags:
            updates["tags"] = tags
        else:
            deletes.append("tags")

        note = note_text.strip()
        if note:
            updates["note"] = note
        else:
            deletes.append("note")

        command = UpdateLinkCommand(
            self._project, link_id, updates=updates, deletes=deletes
        )
        self._command_history.execute(command)
        self._set_dirty(True)
        self._refresh_links_panel(selected_id=link_id)

    def _validate_project(self) -> None:
        """Validate the current project against the schema."""
        project_data = self._project.to_dict()
        errors = validate_project(project_data)
        if not errors:
            self._messagebox.showinfo(
                title="Kleuw", message="Project validation successful: No errors found."
            )
        else:
            error_message = "Project validation failed with the following errors:\n\n"
            error_message += "\n".join(f"- {error}" for error in errors)
            self._messagebox.showwarning(title="Kleuw", message=error_message)

    def _export_summary(self) -> None:
        """Export a text summary of the project."""
        path = self._filedialog.asksaveasfilename(
            title="Export Project Summary",
            filetypes=(("Text files", "*.txt"), ("All files", "*.*")),
            defaultextension=".txt",
        )
        if not path:
            return

        try:
            annotated = self._annotate_links_with_staleness()
        except ValueError as exc:
            self._messagebox.showerror(title="Kleuw", message=str(exc))
            return

        file_entries: list[dict[str, Any]] = [
            entry for entry in self._project.files if isinstance(entry, dict)
        ]
        total_links = len(annotated)
        stale_links = sum(1 for _entry, result in annotated if result.stale)

        try:
            string_io = io.StringIO()
            _export_as_text(
                file=string_io,
                files=file_entries,
                links=annotated,
                total_links=total_links,
                stale_links=stale_links,
            )
            summary_content = string_io.getvalue()
            Path(path).write_text(summary_content, encoding="utf-8")
            self._messagebox.showinfo(
                title="Kleuw", message=f"Successfully exported summary to '{path}'."
            )
        except (OSError, ValueError) as exc:
            self._messagebox.showerror(
                title="Kleuw", message=f"Could not export summary to '{path}':\n{exc}"
            )

    def _set_dirty(self, is_dirty: bool) -> None:
        self._is_dirty = is_dirty
        self.dirty_var.set("● Unsaved changes" if is_dirty else "● Clean")

    def run(self) -> None:
        """Start the Tkinter main loop."""

        self.root.mainloop()


def _format_optional(value: object | None) -> str:
    """Return a placeholder when ``value`` is ``None`` or empty."""
    if value is None:
        return "-"
    text = str(value)
    return text if text.strip() else "-"


def _normalize_hash_object(value: object | None) -> tuple[str, str] | None:
    """Return a ``(algo, value)`` tuple for hash-like ``value``."""
    if isinstance(value, (HashDigest, RegionHash)):
        return value.algo, value.value
    if isinstance(value, Mapping):
        algo = value.get("algo")
        digest_value = value.get("value")
        if isinstance(algo, str) and isinstance(digest_value, str):
            return algo, digest_value
    return None


def _format_hash(hash_value: object | None) -> str:
    """Format ``hash_value`` into ``algo:value`` or ``-`` when missing."""
    digest = _normalize_hash_object(hash_value)
    if digest is None:
        return "-"
    algo, value = digest
    return f"{algo}:{value}"


def _print_table(
    headers: Sequence[str], rows: Sequence[Sequence[str]], *, file: TextIO
) -> None:
    """Render ``rows`` under ``headers`` in a simple fixed-width table."""
    widths = [len(header) for header in headers]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))

    header_line = "  ".join(
        header.ljust(width) for header, width in zip(headers, widths, strict=False)
    )
    print(header_line, file=file)
    for row in rows:
        line = "  ".join(
            cell.ljust(width) for cell, width in zip(row, widths, strict=False)
        )
        print(line, file=file)


def _format_target_for_summary(target: object | None) -> str:
    """Render a ``target`` mapping into ``location[:lines]`` form."""
    if not isinstance(target, Mapping):
        return "-"
    location = str(target.get("file_id") or target.get("path") or "-")
    lines = target.get("lines")
    if isinstance(lines, Mapping):
        start = lines.get("start")
        end = lines.get("end")
        if isinstance(start, int):
            line_suffix = f":{start}"
            if isinstance(end, int) and end != start:
                line_suffix = f":{start}-{end}"
            location = f"{location}{line_suffix}"
    return location


def _format_reasons(reasons: Sequence[str]) -> str:
    """Return a friendly representation of staleness ``reasons``."""
    if not reasons:
        return "-"
    return "; ".join(reasons)


def _export_as_text(
    *,
    file: TextIO,
    files: Sequence[Mapping[str, Any]],
    links: Sequence[tuple[Mapping[str, Any], LinkStalenessResult]],
    total_links: int,
    stale_links: int,
) -> None:
    """Emit human-readable tables describing files and links."""
    file_rows: list[list[str]] = []
    for entry in files:
        file_rows.append(
            [
                str(entry.get("id", "")),
                str(entry.get("path", "")),
                _format_optional(entry.get("lang")),
                _format_hash(entry.get("hash")),
                _format_optional(entry.get("note")),
            ]
        )

    print("Files:", file=file)
    _print_table(["ID", "PATH", "LANG", "HASH", "NOTE"], file_rows, file=file)
    if not file_rows:
        print("(no files)", file=file)
    print(file=file)

    link_rows: list[list[str]] = []
    for entry, result in links:
        link_rows.append(
            [
                str(entry.get("id", "")),
                str(entry.get("type", "")),
                _format_target_for_summary(entry.get("src")),
                _format_target_for_summary(entry.get("dst")),
                "STALE" if result.stale else "OK",
                _format_reasons(result.reasons),
            ]
        )

    print("Links:", file=file)
    _print_table(
        ["ID", "TYPE", "SRC", "DST", "STATUS", "DETAILS"], link_rows, file=file
    )
    if not link_rows:
        print("(no links)", file=file)
    print(file=file)

    print(f"Total links: {total_links}", file=file)
    print(f"Stale links: {stale_links}", file=file)
    print(f"Exported links: {len(links)}", file=file)


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
