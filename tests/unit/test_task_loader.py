"""Tests for task loading."""

from __future__ import annotations

import pytest

from retort.playpen.task_loader import list_bundled_tasks, load_task


class TestBundledTasks:
    def test_list_bundled_tasks(self):
        tasks = list_bundled_tasks()
        assert "rest-api-crud" in tasks
        assert "cli-data-pipeline" in tasks
        assert "react-dashboard" in tasks

    def test_load_bundled_rest_api(self):
        task = load_task("bundled://rest-api-crud")
        assert task.name == "rest-api-crud"
        assert task.prompt
        assert task.description
        assert task.validation_script is not None
        assert task.timeout_minutes == 20

    def test_load_bundled_cli_pipeline(self):
        task = load_task("bundled://cli-data-pipeline")
        assert task.name == "cli-data-pipeline"
        assert task.timeout_minutes == 15

    def test_load_bundled_react_dashboard(self):
        task = load_task("bundled://react-dashboard")
        assert task.name == "react-dashboard"
        assert task.timeout_minutes == 20

    def test_load_nonexistent_bundled(self):
        with pytest.raises(FileNotFoundError, match="not found"):
            load_task("bundled://nonexistent-task")

    def test_unsupported_scheme(self):
        with pytest.raises(ValueError, match="Unsupported task source"):
            load_task("ftp://something")


class TestLocalTasks:
    def test_load_local_task(self, tmp_path):
        task_dir = tmp_path / "my-task"
        task_dir.mkdir()
        (task_dir / "task.yaml").write_text(
            "name: my-task\ndescription: A test task\nprompt: Do the thing\ntimeout_minutes: 10\n"
        )
        task = load_task(f"local://{task_dir}")
        assert task.name == "my-task"
        assert task.timeout_minutes == 10

    def test_load_local_missing_yaml(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="No task.yaml"):
            load_task(f"local://{tmp_path}")


class TestGithubScheme:
    """github:// is a thin shorthand for git://github.com/<owner>/<repo>.

    These tests cover URI parsing only — actually cloning is covered by
    integration tests so unit tests stay offline-friendly.
    """

    def test_missing_repo_raises(self):
        with pytest.raises(ValueError, match="requires owner/repo"):
            load_task("github://brazil-bench")

    def test_empty_owner_raises(self):
        with pytest.raises(ValueError, match="requires owner/repo"):
            load_task("github:///repo")

    def test_parse_with_spec_path(self, monkeypatch):
        # Stub out _load_from_git so we don't actually clone; capture args.
        captured: dict = {}

        def fake_load(url, *, spec_path=None):
            captured["url"] = url
            captured["spec_path"] = spec_path
            from retort.playpen.runner import TaskSpec
            return TaskSpec(name="x", description="", prompt="", timeout_minutes=1)

        monkeypatch.setattr("retort.playpen.task_loader._load_from_git", fake_load)
        load_task("github://brazil-bench/benchmark-template/spec.md")
        assert captured["url"] == "https://github.com/brazil-bench/benchmark-template.git"
        assert captured["spec_path"] == "spec.md"

    def test_parse_without_spec_path(self, monkeypatch):
        captured: dict = {}

        def fake_load(url, *, spec_path=None):
            captured["url"] = url
            captured["spec_path"] = spec_path
            from retort.playpen.runner import TaskSpec
            return TaskSpec(name="x", description="", prompt="", timeout_minutes=1)

        monkeypatch.setattr("retort.playpen.task_loader._load_from_git", fake_load)
        load_task("github://owner/repo")
        assert captured["url"] == "https://github.com/owner/repo.git"
        assert captured["spec_path"] is None

    def test_nested_spec_path(self, monkeypatch):
        captured: dict = {}

        def fake_load(url, *, spec_path=None):
            captured["spec_path"] = spec_path
            from retort.playpen.runner import TaskSpec
            return TaskSpec(name="x", description="", prompt="", timeout_minutes=1)

        monkeypatch.setattr("retort.playpen.task_loader._load_from_git", fake_load)
        load_task("github://owner/repo/docs/spec.md")
        # spec_path captures everything after owner/repo, including subdirs.
        assert captured["spec_path"] == "docs/spec.md"
