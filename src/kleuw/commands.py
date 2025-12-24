"""Undo/redo command framework for Kleuw.

This module provides a basic command pattern implementation to support undo and
redo operations in the Kleuw GUI.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Generic, TypeVar

if TYPE_CHECKING:
    from kleuw.project import Project

T = TypeVar("T")


class Command(ABC, Generic[T]):
    """Abstract base class for a reversible command."""

    @abstractmethod
    def execute(self) -> T | None:
        """Execute the command, returning an optional result."""
        raise NotImplementedError  # pragma: no cover

    @abstractmethod
    def undo(self) -> None:
        """Undo the command's effects."""
        raise NotImplementedError  # pragma: no cover


class CommandHistory:
    """A stack-based history of commands to support undo/redo."""

    def __init__(self) -> None:
        self._undo_stack: list[Command[Any]] = []
        self._redo_stack: list[Command[Any]] = []

    def execute(self, command: Command[T]) -> T | None:
        """Execute a command and push it onto the undo stack."""
        result = command.execute()
        self._undo_stack.append(command)
        self._redo_stack.clear()
        return result

    def undo(self) -> None:
        """Undo the most recent command."""
        if not self._undo_stack:
            return
        command = self._undo_stack.pop()
        command.undo()
        self._redo_stack.append(command)

    def redo(self) -> None:
        """Redo the most recently undone command."""
        if not self._redo_stack:
            return
        command = self._redo_stack.pop()
        command.execute()
        self._undo_stack.append(command)

    def clear(self) -> None:
        """Clear the command history."""
        self._undo_stack.clear()
        self._redo_stack.clear()

    @property
    def can_undo(self) -> bool:
        """Return True if there are commands that can be undone."""
        return bool(self._undo_stack)

    @property
    def can_redo(self) -> bool:
        """Return True if there are commands that can be redone."""
        return bool(self._redo_stack)


class CreateLinkCommand(Command[dict[str, Any]]):
    """A command to create a new link in a project."""

    def __init__(self, project: Project, link_data: dict[str, Any]) -> None:
        self._project = project
        self._link_data = link_data
        self._link_id = str(self._link_data.get("id", ""))

    def execute(self) -> dict[str, Any]:
        """Add the link to the project."""
        self._project.add_link(self._link_data)
        return self._link_data

    def undo(self) -> None:
        """Remove the link from the project."""
        self._project.remove_link(self._link_id)
