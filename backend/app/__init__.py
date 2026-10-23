from pathlib import Path

from flask import Flask, send_from_directory
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from .config import Config
from .extensions import db
from .models import User

csrf = CSRFProtect()
login_manager = LoginManager()
login_manager.login_view = "main.login"
login_manager.login_message = "Vui lòng đăng nhập để tiếp tục."
login_manager.login_message_category = "info"
migrate = Migrate()


@login_manager.user_loader
def load_user(user_id: str):
    try:
        return db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None


def create_app(config_class=Config):
    frontend = Path(__file__).resolve().parents[2] / "frontend"
    app = Flask(__name__, template_folder=str(frontend))
    app.config.from_object(config_class)
    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db, directory=str(Path(__file__).resolve().parents[1] / "migrations"))

    from .routes import main

    app.register_blueprint(main)

    @app.get("/healthz")
    def healthz():
        try:
            db.session.execute(text("SELECT 1"))
            return {"status": "ok", "database": "ok"}, 200
        except SQLAlchemyError:
            db.session.rollback()
            return {"status": "unavailable", "database": "unavailable"}, 503

    @app.get("/css/<path:filename>")
    def css_assets(filename):
        return send_from_directory(frontend / "css", filename)

    @app.get("/js/<path:filename>")
    def js_assets(filename):
        return send_from_directory(frontend / "js", filename)

    @app.template_filter("vnd")
    def format_vnd(value):
        try:
            return f"{int(value):,}".replace(",", ".") + " ₫"
        except (ValueError, TypeError):
            return "0 ₫"

    return app
