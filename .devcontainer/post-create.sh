#!/usr/bin/env bash
set -euo pipefail

# Install the project in editable mode with all extras
pip install --no-cache-dir -e ".[dev,test]"

# Install pre-commit hooks if .pre-commit-config.yaml exists
if [ -f .pre-commit-config.yaml ]; then
    pre-commit install
fi

echo "retort dev environment ready."
