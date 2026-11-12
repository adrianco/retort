"""Hermes >= v0.23.0 runs the agent in a detached gateway daemon; retort stops it per run."""

from __future__ import annotations

import subprocess as sp

from retort.playpen import local_runner


def test_stop_hermes_gateway_calls_the_runs_own_binary(monkeypatch):
    calls = []

    def run(cmd, **kw):
        calls.append(cmd)
        return sp.CompletedProcess(cmd, 0, stdout="Stopped", stderr="")

    monkeypatch.setattr(local_runner.subprocess, "run", run)
    assert local_runner._stop_hermes_gateway("/opt/hermes/bin/hermes") is True
    assert calls == [["/opt/hermes/bin/hermes", "gateway", "stop"]]


def test_stop_hermes_gateway_failure_is_reported_not_raised(monkeypatch):
    def run(cmd, **kw):
        raise sp.TimeoutExpired(cmd, 60)

    monkeypatch.setattr(local_runner.subprocess, "run", run)
    assert local_runner._stop_hermes_gateway("hermes") is False
