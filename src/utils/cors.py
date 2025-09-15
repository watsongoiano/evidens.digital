"""Utilities to harden CORS behavior across the application."""

from __future__ import annotations

from flask import Flask, Response

_PRIVATE_NETWORK_HEADER = "Access-Control-Allow-Private-Network"


def sanitize_private_network_header(response: Response) -> Response:
    """Strip the Access-Control-Allow-Private-Network header if present."""
    response.headers.pop(_PRIVATE_NETWORK_HEADER, None)
    return response


def register_private_network_sanitizer(app: Flask) -> None:
    """Ensure every response emitted by *app* has the private network header removed."""

    @app.after_request
    def _remove_private_network_header(response: Response) -> Response:  # pragma: no cover - exercised via tests
        return sanitize_private_network_header(response)

