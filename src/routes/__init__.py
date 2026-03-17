"""API route handlers

Expose routers here so `from src.routes import auth, data` works.
"""

from . import auth, data

__all__ = ["auth", "data"]
