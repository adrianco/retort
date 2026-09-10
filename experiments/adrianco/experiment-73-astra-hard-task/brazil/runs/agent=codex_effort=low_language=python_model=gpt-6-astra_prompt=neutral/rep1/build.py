"""Build a portable Python zipapp using only the standard library.

Run the result with --data-dir pointing to the supplied CSV directory.
"""
import argparse
from pathlib import Path
import shutil
import tempfile
import zipapp


def build(output='dist/brazilian-soccer-mcp.pyz'):
    root = Path(__file__).resolve().parent
    target = Path(output).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        staging = Path(temporary)
        for filename in ('soccer.py', 'server.py'):
            shutil.copy2(root / filename, staging / filename)
        zipapp.create_archive(staging, target, main='server:main',
                              interpreter='/usr/bin/env python3', compressed=True)
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='dist/brazilian-soccer-mcp.pyz')
    print(build(parser.parse_args().output))
