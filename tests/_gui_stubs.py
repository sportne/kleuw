"""Shared test doubles for Tkinter-dependent tests."""

from __future__ import annotations

from typing import Any


class StubStringVar:
    """Minimal replacement for ``tkinter.StringVar``."""

    def __init__(self, value: str = "") -> None:
        self._value = value

    def set(self, value: str) -> None:
        self._value = value

    def get(self) -> str:
        return self._value


class StubRoot:
    """Headless replacement for ``tkinter.Tk`` used in tests."""

    def __init__(self) -> None:
        self.config_kwargs: dict[str, Any] = {}
        self.bindings: list[tuple[str, Any]] = []

    def title(self, _title: str) -> None:  # pragma: no cover - trivial setter
        return None

    def geometry(self, _geometry: str) -> None:  # pragma: no cover - trivial setter
        return None

    def minsize(self, _width: int, _height: int) -> None:  # pragma: no cover
        return None

    def config(self, **kwargs: Any) -> None:
        self.config_kwargs.update(kwargs)

    def bind(self, sequence: str, handler: Any) -> None:
        self.bindings.append((sequence, handler))

    def mainloop(self) -> None:  # pragma: no cover - not exercised in tests
        return None


class StubMessageBox:
    """Records invocations instead of showing dialogs."""

    def __init__(self) -> None:
        self.info_calls: list[tuple[str, str]] = []
        self.error_calls: list[tuple[str, str]] = []

    def showinfo(self, *, title: str, message: str) -> None:
        self.info_calls.append((title, message))

    def showerror(self, *, title: str, message: str) -> None:
        self.error_calls.append((title, message))
