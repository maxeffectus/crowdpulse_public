import functools

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, current_app, make_response
)

from .common import format_uuid
from .db import get_db
from .http import HttpConnectionError
from .http.api.mediaserver import MediaserverApiV3, MediaserverApiConnectionError, MediaserverApiHttpError, NotFound
from .http.api.plugin import PluginApi

bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'GET':
        return render_template('auth/login.html')
    username = request.form['username']
    password = request.form['password']
    address = '127.0.0.1'
    mediaserver_port = current_app.config['MEDIASERVER_PORT']
    netloc = f'{address}:{mediaserver_port}'
    mediaserver_api = MediaserverApiV3(f'https://{username}:{password}@{netloc}')
    current_app.config.from_mapping({'MEDIASERVER_API': mediaserver_api})
    try:
        mediaserver_api.is_online()
    except MediaserverApiHttpError:
        error = f"Failed to connect to Mediaserver at {netloc} with credentials provided"
        flash(error)
        return render_template('auth/login.html')
    except MediaserverApiConnectionError:
        flash(f"Connection to Mediaserver at {netloc} could not be established.")
    try:
        mediaserver_user_data = mediaserver_api.get_user_by_name(username)
    except NotFound:
        flash(f"Something went wrong: username {username} not found in Mediaserver DB")
        return render_template('auth/login.html')
    plugin_port = current_app.config['CROWDPULSE_PLUGIN_PORT']
    plugin_api = PluginApi(plugin_port)
    current_app.config.from_mapping({'PLUGIN_API': plugin_api})
    token = mediaserver_api.auth_handler.get_token()
    try:
        plugin_api.send_credentials(
            user=username,
            token=token,
            )
        plugin_error = None
    except HttpConnectionError:
        plugin_error = f"Unable to establish connection to CrowdPulse plugin on port {plugin_port}"
    db = get_db()
    user_id_as_str = format_uuid(mediaserver_user_data['id'])
    user_in_db = db.execute(
        'SELECT * FROM user WHERE id = ?', (user_id_as_str, )).fetchone()
    if user_in_db is None:
        db.execute(
            'INSERT INTO user (id, username) '
            'VALUES(?, ?)',
            (user_id_as_str, username),
            )
        db.commit()
    session.clear()
    session['user_id'] = user_id_as_str
    if plugin_error is not None:
        flash(plugin_error)
    response = make_response(redirect(url_for('index')))
    response.set_cookie('x-nx-user-name', username)
    response.set_cookie('x-runtime-guid', token)
    return response


@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
    else:
        db = get_db()
        g.user = db.execute(
            'SELECT * FROM user WHERE id = ?', (user_id,)).fetchone()


@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))


def login_required(view):

    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'))
        return view(**kwargs)

    return wrapped_view


