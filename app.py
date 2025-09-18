from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from flask_login import LoginManager

from src.models.user import User, db
from src.routes.auth import auth_bp
from src.routes.checkup import checkup_bp
from src.routes.checkup_intelligent import checkup_intelligent_bp
from src.routes.database_api import database_api_bp
from src.routes.user import user_bp
from src.utils.analytics import analytics, track_visit
from src.utils.cors import register_private_network_sanitizer
from src.utils.oauth import oauth_provider

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "src" / "static"

# Additional directories that contain public assets (login/dashboard, JS, CSS, etc.)
ADDITIONAL_STATIC_DIRS = [
    BASE_DIR,
    BASE_DIR / "styles",
    BASE_DIR / "js",
    BASE_DIR / "assets",
]

# Allow-list of file extensions that can be served as static assets
ALLOWED_STATIC_EXTENSIONS = {
    ".css",
    ".html",
    ".ico",
    ".jpg",
    ".jpeg",
    ".js",
    ".json",
    ".pdf",
    ".png",
    ".svg",
    ".txt",
    ".webmanifest",
    ".woff",
    ".woff2",
}


def _find_static_asset(path: str) -> tuple[Path, str] | None:
    """Locate a static asset that can be safely served."""

    if not path:
        path = "index.html"

    candidate = Path(path)

    # Prevent path traversal attempts like "../../etc/passwd"
    if any(part == ".." for part in candidate.parts):
        return None

    candidates = [candidate]
    if candidate.suffix:
        if candidate.suffix.lower() not in ALLOWED_STATIC_EXTENSIONS:
            return None
    else:
        candidates.append(candidate.with_suffix(".html"))

    search_dirs = [STATIC_DIR, *ADDITIONAL_STATIC_DIRS]

    for base_dir in search_dirs:
        if not base_dir.exists():
            continue

        resolved_base = base_dir.resolve()
        for option in candidates:
            absolute = (resolved_base / option).resolve()
            try:
                relative = absolute.relative_to(resolved_base)
            except ValueError:
                continue

            if absolute.is_file() and absolute.suffix.lower() in ALLOWED_STATIC_EXTENSIONS:
                return resolved_base, relative.as_posix()

    return None


def create_app(config: dict | None = None) -> Flask:
    """Application factory used by tests and production deployments."""

    app = Flask(__name__, static_folder=str(STATIC_DIR))

    database_path = BASE_DIR / "src" / "database" / "app.db"
    os.makedirs(database_path.parent, exist_ok=True)

    app.config.update(
        SECRET_KEY=os.getenv("SECRET_KEY", "asdf#FGSgvasgf$5$WGT"),
        SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL", f"sqlite:///{database_path}"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    if os.getenv("TESTING", "").lower() == "true":
        app.config["TESTING"] = True

    if config:
        app.config.update(config)

    # Initialize extensions
    CORS(app, supports_credentials=True)
    register_private_network_sanitizer(app)
    db.init_app(app)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "serve"
    login_manager.session_protection = "strong"

    @login_manager.user_loader
    def load_user(user_id: str):  # pragma: no cover - simple database lookup
        if user_id is None:
            return None
        try:
            return User.query.get(int(user_id))
        except (TypeError, ValueError):
            return None

    @login_manager.unauthorized_handler
    def handle_unauthorized():
        return jsonify({"ok": False, "error": "NOT_AUTHENTICATED"}), 401

    oauth_provider.init_app(app)

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp, url_prefix="/api")
    app.register_blueprint(checkup_bp, url_prefix="/api")
    app.register_blueprint(checkup_intelligent_bp, url_prefix="/api")
    app.register_blueprint(database_api_bp)

    @app.route("/favicon.png")
    def serve_favicon_png():
        """Serve the PNG favicon stored at the project root."""
        favicon_path = BASE_DIR / "favicon.png"
        if favicon_path.exists():
            return send_from_directory(favicon_path.parent, favicon_path.name)
        return "", 404

    @app.route("/analytics/stats")
    def get_analytics_stats():
        """Endpoint para visualizar estatísticas de acesso"""
        return jsonify(analytics.get_summary())

    @app.route("/analytics/full")
    def get_full_analytics():
        """Endpoint para visualizar estatísticas completas (admin)"""
        return jsonify(analytics.get_stats())

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    @track_visit()
    def serve(path: str):
        # Não interceptar rotas da API
        if path.startswith("api/"):
            return "API route not found", 404

        asset_info = _find_static_asset(path)
        if asset_info:
            base_dir, relative_path = asset_info
            return send_from_directory(base_dir, relative_path)

        fallback = _find_static_asset("index.html")
        if fallback:
            base_dir, relative_path = fallback
            return send_from_directory(base_dir, relative_path)

        return "index.html not found", 404

    with app.app_context():
        if not app.config.get("TESTING"):
            db.create_all()

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=False)
