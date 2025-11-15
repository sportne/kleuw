"""Pytest plugin hooks that tailor coverage behavior for Kleuw."""

from __future__ import annotations

import pytest

GUI_ONLY_MARK_EXPRESSION = "gui"
GUI_ONLY_COVERAGE_SOURCES: tuple[str, ...] = ("kleuw.gui",)


def _is_gui_only_run(config: pytest.Config) -> bool:
    return (config.option.markexpr or "").strip() == GUI_ONLY_MARK_EXPRESSION


def pytest_configure(config: pytest.Config) -> None:
    """Relax coverage requirements when executing only GUI tests."""

    if not _is_gui_only_run(config):
        return

    config.option.cov_source = list(GUI_ONLY_COVERAGE_SOURCES)
    config.option.cov_fail_under = 0

    cov_plugin = config.pluginmanager.getplugin("_cov")
    if cov_plugin is None:
        return

    cov_plugin.options.cov_source = list(GUI_ONLY_COVERAGE_SOURCES)
    cov_plugin.options.cov_fail_under = 0

    if cov_plugin.cov_controller is not None:
        cov_plugin.cov_controller.cov.config.source = list(GUI_ONLY_COVERAGE_SOURCES)
