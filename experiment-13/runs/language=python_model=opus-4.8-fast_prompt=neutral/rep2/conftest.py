"""Ensure the repository root (containing the `bsoccer` package) is importable
when running the test suite from any working directory."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
