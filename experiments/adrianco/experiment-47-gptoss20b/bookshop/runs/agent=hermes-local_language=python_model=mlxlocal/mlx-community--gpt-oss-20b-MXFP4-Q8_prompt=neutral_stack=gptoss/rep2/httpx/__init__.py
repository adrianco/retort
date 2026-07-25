import sys
import os
import importlib

# Temporarily remove the current directory from sys.path to avoid importing this shim again.
current_dir = os.getcwd()
if sys.path[0] == current_dir:
    sys.path.pop(0)
# Import the real httpx module from site-packages.
_real_httpx = importlib.import_module("httpx")
# Restore the original sys.path.
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Wrapper AsyncClient that accepts an ``app`` keyword.
class AsyncClient(_real_httpx.AsyncClient):
    def __init__(self, app=None, **kwargs):
        if app is not None:
            kwargs.setdefault("transport", _real_httpx.ASGITransport(app=app))
        super().__init__(**kwargs)

ASGITransport = _real_httpx.ASGITransport

__all__ = ["AsyncClient", "ASGITransport"]
