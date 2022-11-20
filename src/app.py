"""
    Init environement and entrypoint to application
"""

from dotenv import load_dotenv
from flask import Flask
from src.web.handlers import handlers


def create_app() -> Flask:
    dotenv_path = "../.env"
    load_dotenv(dotenv_path)

    app = Flask(__name__)

    app.register_blueprint(handlers)

    return app

if __name__ == "__main__":
    create_app().run(debug = True)
