from flask import Flask

from app.repositories.project_repo import _init_projects_db
from app.routes.agent_routes import agent_bp
from app.routes.export_routes import export_bp
from app.routes.page_routes import page_bp
from app.routes.project_routes import project_bp
from app.routes.video_routes import video_bp


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")

    app.register_blueprint(page_bp)
    app.register_blueprint(project_bp)
    app.register_blueprint(agent_bp)
    app.register_blueprint(video_bp)
    app.register_blueprint(export_bp)

    _init_projects_db()
    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)