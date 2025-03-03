import os

from flask import Flask

from . import auth
from . import db
from . import engagement_threshold
from . import events
from . import handle_metadata


def create_app(config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',  # TODO: To be updated after active development phase is over
        DATABASE=os.path.join(app.instance_path, 'flaskr.sqlite'),
        )
    if config is None:
        app.config.from_pyfile('config.py', silent=True)
    else:
        app.config.from_mapping(config)
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    db.init_app(app)
    app.register_blueprint(auth.bp)
    app.register_blueprint(events.bp)
    app.register_blueprint(handle_metadata.bp)
    app.register_blueprint(engagement_threshold.bp)
    app.add_url_rule('/', endpoint='index')
    return app
