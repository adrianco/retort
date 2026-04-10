"""Constructs agent prompts from task specifications and stack configuration."""

from __future__ import annotations

from retort.playpen.runner import StackConfig, TaskSpec


def build_prompt(task: TaskSpec, stack: StackConfig) -> str:
    """Build the full prompt for an agent given a task and stack config.

    The prompt includes the task description, technology constraints,
    and any framework-specific guidance.
    """
    sections = [
        f"# Task: {task.name}",
        "",
        task.description,
        "",
        "## Technology Stack",
        f"- **Language**: {stack.language}",
        f"- **Framework**: {stack.framework}",
    ]

    if stack.extra:
        for key, value in stack.extra.items():
            sections.append(f"- **{key.replace('_', ' ').title()}**: {value}")

    sections.extend([
        "",
        "## Instructions",
        "",
        task.prompt,
    ])

    if task.validation_script:
        sections.extend([
            "",
            "## Validation",
            "Your solution will be validated automatically. Ensure all tests pass.",
        ])

    return "\n".join(sections)
