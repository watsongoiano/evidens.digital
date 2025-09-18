"""WSGI entrypoint for the Vercel deployment."""
from __future__ import annotations

from app import create_app

app = create_app()


def handler(request):
    """Vercel-compatible handler."""
    return app(request.environ, lambda *args: None)


if __name__ == "__main__":
    app.run(debug=True)
