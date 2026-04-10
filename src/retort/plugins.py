"""Pluggy-based plugin system for retort.

Defines hook specifications for custom scorers and runners, and provides
a plugin manager with entry-point discovery.

Plugin authors implement hooks and register via the ``retort.plugins``
entry-point group in their package's pyproject.toml::

    [project.entry-points."retort.plugins"]
    my_plugin = "my_package.retort_plugin"
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pluggy

if TYPE_CHECKING:
    from retort.playpen.runner import PlaypenRunner
    from retort.scoring.registry import Scorer

PROJECT_NAME = "retort"

hookspec = pluggy.HookspecMarker(PROJECT_NAME)
hookimpl = pluggy.HookimplMarker(PROJECT_NAME)

logger = logging.getLogger(__name__)


class RetortHookSpec:
    """Hook specifications for retort plugins."""

    @hookspec
    def retort_register_scorers(self) -> list[Scorer]:
        """Return a list of Scorer instances to register.

        Each scorer must satisfy the ``Scorer`` protocol (``name`` property
        and ``score()`` method).
        """

    @hookspec
    def retort_register_runners(self) -> dict[str, PlaypenRunner]:
        """Return a mapping of runner-name → PlaypenRunner instance.

        The name is used to select the runner via config or CLI
        (e.g. ``runner: my_custom_runner`` in workspace.yaml).
        """


def _create_plugin_manager() -> pluggy.PluginManager:
    """Create a fresh PluginManager with retort hookspecs registered."""
    pm = pluggy.PluginManager(PROJECT_NAME)
    pm.add_hookspecs(RetortHookSpec)
    return pm


def get_plugin_manager() -> pluggy.PluginManager:
    """Return a PluginManager with entry-point plugins loaded.

    Plugins are discovered from the ``retort.plugins`` entry-point group.
    """
    pm = _create_plugin_manager()
    pm.load_setuptools_entrypoints(PROJECT_NAME)
    return pm


def discover_scorers(pm: pluggy.PluginManager | None = None) -> list[Scorer]:
    """Discover scorer plugins via pluggy hooks.

    Returns a flat list of all Scorer instances returned by all plugins.
    """
    if pm is None:
        pm = get_plugin_manager()

    scorers: list[Scorer] = []
    results = pm.hook.retort_register_scorers()
    for batch in results:
        if batch:
            scorers.extend(batch)
    return scorers


def discover_runners(
    pm: pluggy.PluginManager | None = None,
) -> dict[str, PlaypenRunner]:
    """Discover runner plugins via pluggy hooks.

    Returns a merged dict of runner-name → PlaypenRunner from all plugins.
    """
    if pm is None:
        pm = get_plugin_manager()

    runners: dict[str, PlaypenRunner] = {}
    results = pm.hook.retort_register_runners()
    for batch in results:
        if batch:
            runners.update(batch)
    return runners


def list_plugins(pm: pluggy.PluginManager | None = None) -> list[dict[str, str]]:
    """Return metadata for all registered plugins.

    Each entry has ``name`` and ``module`` keys.
    """
    if pm is None:
        pm = get_plugin_manager()

    infos: list[dict[str, str]] = []
    for plugin in pm.get_plugins():
        if plugin is pm.trace:
            continue
        name = pm.parse_hookimpl_opts(plugin, "__name__") or ""
        mod = getattr(plugin, "__name__", None) or type(plugin).__module__
        dist = pm.parse_hookimpl_opts(plugin, "__name__")
        plugin_name = getattr(plugin, "__name__", None) or type(plugin).__name__
        infos.append({"name": plugin_name, "module": mod})
    return infos
