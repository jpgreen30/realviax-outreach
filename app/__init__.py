# App package
try:
    from .main import app
except ImportError:
    # Allow importing the package without FastAPI for non-web contexts (e.g., scripts)
    app = None

__all__ = ["app"]