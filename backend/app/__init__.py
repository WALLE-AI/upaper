"""Application factory and blueprint registration."""
from __future__ import annotations

from flask import Flask

from .config import BaseConfig
from .db.session import db
from .api.health.routes import bp as health_bp
from .api.users.routes import bp as users_bp
from .api.papers.routes import bp as papers_bp
from .docs.routes import bp as docs_bp
from .errors import register_error_handlers
from .integrations.supabase_client import supabase_ext
from flask_cors import CORS


def create_app(config_class: type[BaseConfig] | None = None) -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)
    CORS(app, resources={r"/api/*": {"origins": "http://localhost:4173"}})
    app.config.from_object(config_class or BaseConfig())

    # Init extensions
    db.init_app(app)
    supabase_ext.init_app(app)

    # Register blueprints
    app.register_blueprint(health_bp, url_prefix="/api/health")
    app.register_blueprint(users_bp, url_prefix="/api/users")
    app.register_blueprint(papers_bp, url_prefix="/api/papers")
    app.register_blueprint(docs_bp)

    # Global error handlers
    register_error_handlers(app)
    return app

# def list_routes():
#     routes = []
#     for rule in create_app.url_map.iter_rules():
#         routes.append({
#             'endpoint': rule.endpoint,
#             'methods': list(rule.methods),
#             'path': str(rule)
#         })
#     print(routes)
