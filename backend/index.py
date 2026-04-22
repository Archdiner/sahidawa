"""Vercel entrypoint — re-exports the FastAPI app for the Python runtime."""

from app.main import app  # noqa: F401
