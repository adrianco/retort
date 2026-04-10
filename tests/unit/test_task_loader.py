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
