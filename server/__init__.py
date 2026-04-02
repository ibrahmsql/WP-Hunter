"""Temodar Agent Server package."""


def create_app():
    """Lazily import and return the FastAPI application instance."""
    from server.app import create_app as _create_app

    return _create_app()


__all__ = ["create_app"]
