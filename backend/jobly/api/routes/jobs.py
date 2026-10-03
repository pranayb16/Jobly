"""Compatibility import for callers using the old route module."""

from jobly.products.jobs.routes import router

__all__ = ["router"]
