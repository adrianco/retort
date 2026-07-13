"""Configuration for the Brazilian Soccer MCP Server."""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Config:
    data_dir: str = os.environ.get(
        'BRAZILIAN_SOCCER_DATA_DIR',
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'kaggle'),
    )
    default_limit: int = int(os.environ.get('BRAZILIAN_SOCCER_DEFAULT_LIMIT', '20'))
    max_results: int = int(os.environ.get('BRAZILIAN_SOCCER_MAX_RESULTS', '200'))
