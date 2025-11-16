"""Tests for the Kleuw-specific pytest plugin hooks."""

from __future__ import annotations

import importlib
from types import SimpleNamespace

from kleuw import pytest_plugin as _pytest_plugin

pytest_plugin = importlib.reload(_pytest_plugin)


class _StubPluginManager:
    def __init__(self, plugin: object | None) -> None:
        self._plugin = plugin

    def getplugin(self, name: str) -> object | None:
        if name == "_cov":
            return self._plugin
        return None


class _StubConfig(SimpleNamespace):
    pass


class _StubCoveragePlugin:
    def __init__(self) -> None:
        self.options = SimpleNamespace(cov_source=None, cov_fail_under=None)
        self.cov_controller = SimpleNamespace(
            cov=SimpleNamespace(config=SimpleNamespace(source=None))
        )


def test_is_gui_only_run_detects_marker() -> None:
    config = _StubConfig(option=SimpleNamespace(markexpr="gui"))
    assert pytest_plugin._is_gui_only_run(config)
    config.option.markexpr = "not-gui"
    assert not pytest_plugin._is_gui_only_run(config)


def test_pytest_configure_updates_coverage_when_marked() -> None:
    cov_plugin = _StubCoveragePlugin()
    config = _StubConfig(
        option=SimpleNamespace(markexpr="gui", cov_source=None, cov_fail_under=80),
        pluginmanager=_StubPluginManager(cov_plugin),
    )

    pytest_plugin.pytest_configure(config)

    assert config.option.cov_source == list(pytest_plugin.GUI_ONLY_COVERAGE_SOURCES)
    assert config.option.cov_fail_under == 0
    assert cov_plugin.options.cov_source == list(
        pytest_plugin.GUI_ONLY_COVERAGE_SOURCES
    )
    assert cov_plugin.options.cov_fail_under == 0
    assert cov_plugin.cov_controller.cov.config.source == list(
        pytest_plugin.GUI_ONLY_COVERAGE_SOURCES
    )


def test_pytest_configure_ignores_non_gui_runs() -> None:
    config = _StubConfig(
        option=SimpleNamespace(markexpr="", cov_source=None, cov_fail_under=80),
        pluginmanager=_StubPluginManager(None),
    )

    pytest_plugin.pytest_configure(config)

    assert config.option.cov_source is None
    assert config.option.cov_fail_under == 80
