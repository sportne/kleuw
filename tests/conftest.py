"""Project-wide pytest fixtures."""

from unittest.mock import MagicMock

import pytest

pytest_plugins = ("tests.test_gui_files",)


@pytest.fixture()
def mock_tkinter(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Replace the `tkinter` and `ttk` modules with mocks."""
    mock_tk = MagicMock(name="tkinter")
    mock_ttk = MagicMock(name="ttk")
    monkeypatch.setattr("kleuw.gui.tk", mock_tk)
    monkeypatch.setattr("kleuw.gui.ttk", mock_ttk)
    mock_tk.Tk.return_value = MagicMock(name="Tk")
    return mock_tk
