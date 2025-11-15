# Kleuw UI Design Specification

[Back to Overview](kleuw_overall_spec.md)

## 1. Purpose

This document defines the **graphical user interface (GUI)** requirements and design for **Kleuw**, using only the Python standard library (notably `tkinter`).

The GUI enables users to:

* View one or two files side-by-side
* Select line ranges visually
* Create, edit, and delete relationships
* Inspect link metadata
* Check for stale relationships

This document guides implementation but includes **no code**.

---

## 2. Top-Level UI Layout

### Main Window Structure

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Menu Bar: File | Edit | View | Links | Tools | Help                         │
├─────────────────────────────────────────────────────────────────────────────┤
│ Toolbar: [New] [Open] [Save] | [Add File] [Check Staleness] [Create Link]   │
├───────────────┬─────────────────────────────────────────────────────────────┤
│ Files Panel    │ Link Workspace                                              │
│ (project)      │                                                             │
│  - file list   │  ┌────────────────────────┬────────────────────────┐        │
│  - add/remove  │  │ Left Viewer            │ Right Viewer           │        │
│                │  │ (line nums + text)     │ (line nums + text)    │        │
│                │  └────────────────────────┴────────────────────────┘        │
│                │  Relationship: [Combo] [Swap ↔] [Create Link]               │
├───────────────┴─────────────────────────────────────────────────────────────┤
│ Links Panel (table of existing links)                                        │
└─────────────────────────────────────────────────────────────────────────────┘
Status Bar (project path, dirty flag, selection summary)
```

---

## 3. UI Components

### 3.1 Menu Bar

**File**

* New Project
* Open Project
* Save
* Save As
* Recent Projects
* Exit

**Edit**

* Undo
* Redo
* Delete Link
* Preferences

**View**

* Toggle Files Panel
* Toggle Links Panel
* Increase Font Size
* Decrease Font Size
* Toggle Line Wrapping

**Links**

* Create Link
* Edit Link
* Delete Link
* Check Staleness
* Recompute Hashes

**Tools**

* Validate Project
* Export Summary

**Help**

* About
* Keyboard Shortcuts

---

## 4. Toolbar

The toolbar contains quick-access buttons:

* **New** – create a new empty Kleuw project
* **Open** – load an existing project
* **Save** – save the current project
* **Add File** – add a source file to the project
* **Check Staleness** – recompute region hashes for all links
* **Create Link** – create a new link from current selections

Buttons should provide tooltips.

---

## 5. Files Panel

A left-side vertical panel showing the project’s known files:

### Contents

* **Listbox or Treeview** of file paths
* Buttons: **Add File**, **Remove File**, **Open Left**, **Open Right**

### Behavior

* Double-click a file to open it in the Left viewer
* Shift+Double-click to open in the Right viewer
* Context menu:

  * Open in Left Viewer
  * Open in Right Viewer
  * Remove File

---

## 6. Link Workspace

### 6.1 Side-by-Side Viewers

Two monospaced text widgets with:

* Line numbers (gutter implemented via adjacent canvas or `Text` window)
* Horizontal and vertical scrollbars
* Read-only text
* Line-selection highlighting

### 6.2 File Display Behavior

* Opening a file loads its text (UTF-8 decoding with universal newlines)
* Line endings normalized to `\n` for display consistency
* Large files should be scrollable without freezing

### 6.3 Line Selection Model

* Click-drag selects one or more full lines
* Selection snaps to entire lines (no partial selections)
* Highlight visual feedback for selected block
* Selection summary displayed below as `Left: L13–L27` or `Right: L42–L42`
* Esc key clears selection

### 6.4 Relationship Type Selection

A **ComboBox** to choose a relationship type from the schema-defined enumeration.

### 6.5 Swap Button (↔)

Swaps Left and Right file assignments (both file and selection).

### 6.6 Create Link Button

* Enabled only if:

  * Both Left and Right files are open
  * A relationship type is selected
* Creates a new link using:

  * file paths / file IDs
  * selected line ranges (or whole files if no selection)
  * timestamp
  * region hashes
* Adds link to Links Panel

---

## 7. Links Panel

A table listing all existing links with columns:

* **ID**
* **Type**
* **Source** (file + range)
* **Destination** (file + range)
* **Stale?** (Yes/No)
* **Tags**
* **Notes** (indicator)

### Interactions

* Double-click → load both files in Link Workspace and scroll to linked lines
* Right-click menu:

  * Edit Link
  * Delete Link
  * Recompute Hashes
  * Copy as JSON
  * Copy as text reference (`path#Lstart-Lend`)

Rows are highlighted if a link is stale.

---

## 8. Staleness UI

### 8.1 Visual Marking

* Stale links displayed with yellow background
* Tooltip shows which side changed (src/dst)

### 8.2 Staleness Checking

Accessible via both:

* Toolbar button
* Menu: Links → Check Staleness

### 8.3 Staleness Result Window

A small modal dialog:

```
Staleness Check Complete
------------------------
Total Links: 37
Stale Links: 4

[View Stale Links] [Close]
```

Selecting **View Stale Links** filters the Links Panel.

---

## 9. Status Bar

Displays:

* Project path
* Dirty flag (“● Unsaved changes”)
* Current selection summary (e.g., “Left: L10–L22, Right: L45–L57”)
* Staleness check summary

---

## 10. Keyboard Shortcuts

* Ctrl+N – New Project
* Ctrl+O – Open Project
* Ctrl+S – Save Project
* Ctrl+Enter – Create Link
* Ctrl+K – Check Staleness
* Ctrl++ / Ctrl+- – Increase/Decrease font size
* Alt+W – Toggle wrapping
* Esc – Clear selections

---

## 11. Error Handling

* Display modal dialogs for:

  * Corrupt project file
  * Missing file on disk
  * Unsupported encoding
* Non-blocking toast messages in status bar for minor issues

---

## 12. Preferences (Minimal for v1)

* Default font size
* Default relationship type ordering
* Show/hide line numbers
* Line wrapping default

---

## 13. Accessibility

* Keyboard navigation supports all actions
* Adjustable text size
* High contrast mode toggle

---

## 14. Future Enhancements (Not in v1)

* Syntax highlighting (requires external deps)
* Split-view diff for stale links
* Drag‑and‑drop file loading
* Filterable file tree
* Tabbed multi-file viewer

---

[Back to Overview](kleuw_overall_spec.md)
