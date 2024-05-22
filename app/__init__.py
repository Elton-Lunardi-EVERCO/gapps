from flask import Flask, request, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import exc
from flask_mail import Mail
from config import config
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_babel import Babel, lazy_gettext as _l
import logging
import json
import os
import sys


db = SQLAlchemy()
babel = Babel()
migrate = Migrate()
mail = Mail()
login = LoginManager()
login.login_view = "auth.login"


def create_app(config_name="default"):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s",
        level=app.config["LOG_LEVEL"] or app.config["WORKER_LOG_LEVEL"],
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    configure_models(app)
    registering_blueprints(app)
    configure_extensions(app)

    @app.errorhandler(404)
    def not_found(e):
        if request.path.startswith("/api/"):
            if isinstance(e.description, dict):
                return jsonify(e.description), e.code
            return (
                jsonify({"ok": False, "message": e.description, "code": e.code}),
                e.code,
            )
        return render_template("layouts/errors/default.html", title="Not found"), e.code

    @app.errorhandler(403)
    def not_authorized(e):
        if request.path.startswith("/api/"):
            if isinstance(e.description, dict):
                return jsonify(e.description), e.code
            return (
                jsonify({"ok": False, "message": e.description, "code": e.code}),
                e.code,
            )
        return (
            render_template("layouts/errors/default.html", title="Unauthorized"),
            e.code,
        )

    @app.errorhandler(401)
    def not_authenticated(e):
        if request.path.startswith("/api/"):
            if isinstance(e.description, dict):
                return jsonify(e.description), e.code
            return (
                jsonify({"ok": False, "message": e.description, "code": e.code}),
                e.code,
            )
        return (
            render_template("layouts/errors/default.html", title="Unauthenticated"),
            e.code,
        )

    @app.errorhandler(500)
    def internal_error(e):
        app.logger.error(str(e))
        if request.path.startswith("/api/"):
            if isinstance(e.description, dict):
                return jsonify(e.description), e.code
            return (
                jsonify({"ok": False, "message": e.description, "code": e.code}),
                e.code,
            )
        return (
            render_template("layouts/errors/default.html", title="Internal error"),
            e.code,
        )

    @app.errorhandler(exc.SQLAlchemyError)
    def handle_db_exceptions(e):
        error = str(e)
        app.logger.warning(f"Rolling back database session in app: {error}")
        db.session.rollback()
        if request.path.startswith("/api/"):
            return jsonify({"ok": False, "message": error, "code": 500}), 500
        return (
            render_template("layouts/errors/default.html", title="Internal error"),
            500,
        )

    def to_pretty_json(value):
        return json.dumps(value, sort_keys=True, indent=4, separators=(",", ": "))

    app.jinja_env.filters["tojson_pretty"] = to_pretty_json

    """
    @app.before_request
    def before_request():
        pass
    """
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)

    return app


def configure_models(app):
    app.db = db
    return


def configure_extensions(app):
    db.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)
    babel.init_app(app)
    login.init_app(app)
    return


def registering_blueprints(app):
    from app.main import main as main_blueprint

    app.register_blueprint(main_blueprint)

    from app.api_v1 import api as api_v1_blueprint

    app.register_blueprint(api_v1_blueprint, url_prefix="/api/v1")

    from app.auth import auth as auth_blueprint

    app.register_blueprint(auth_blueprint)
    return
