import datetime
import json
import random
import threading
import time
import uuid
from datetime import timedelta
from typing import Mapping, Any

from flask import Blueprint, render_template, request, flash, redirect, url_for, g, abort, current_app, jsonify

from .auth import login_required
from .common import format_uuid
from .db import get_db
from .handle_metadata import calculate_average_engagement_rate

bp = Blueprint('events', __name__)  # TODO: Add /events url_prefix


@bp.route('/')
@login_required
def index():
    db = get_db()
    events = db.execute(
        'SELECT e.id, start, finish, name, comment, username'
        ' FROM event e JOIN user u ON e.user_id = u.id'
        ' ORDER BY start DESC'
        ).fetchall()
    return render_template('events/index.html', events=events)


@bp.route('/create', methods=('GET', 'POST'))
@login_required
def create():
    db = get_db()
    if request.method == 'GET':
        mediaserver_api = current_app.config.get('MEDIASERVER_API')
        if mediaserver_api is None:
            flash("Mediaserver connection is required to update camera list. Please log in.")
            return redirect(url_for('auth.login'))
        cameras = _get_all_cameras(mediaserver_api, db)
        return render_template('events/create.html', cameras=cameras)
    name = request.form['name']
    start = request.form['start']
    finish = request.form['finish']
    comment = request.form['comment']
    cameras = _get_cameras_from_form(request.form)
    if not start:
        start = datetime.datetime.now().isoformat()
    errors = []
    if not name:
        errors.append('Event name is required.')
    if finish:
        if start > finish:
            errors.append('Event start time is later than finish time.')
    if errors:
        flash('; '.join(errors))
        return render_template('events/create.html')
    event_id = format_uuid(uuid.uuid4())
    db.execute(
        'INSERT INTO event (id, user_id, name, start, finish, comment)'
        ' VALUES (?, ?, ?, ?, ?, ?)',
        (event_id, g.user['id'], name, start, finish, comment),
        )
    if cameras:
        _add_cameras_to_event(cameras, db, event_id)
    db.commit()
    return redirect(url_for('index'))


@bp.route('/<string:id_>/update', methods=('GET', 'POST'))
@login_required
def update(id_):
    mediaserver_api = current_app.config.get('MEDIASERVER_API')
    if mediaserver_api is None:
        flash("Mediaserver connection is required to update camera list. Please log in.")
        return redirect(url_for('auth.login'))
    event = _get_event(id_)
    db = get_db()
    all_cameras = _get_all_cameras(mediaserver_api, db)
    previously_selected_cameras = _get_event_cameras_from_db(db, id_)
    if request.method == 'GET':
        return render_template(
            'events/update.html',
            event=event,
            all_cameras=all_cameras,
            selected_cameras=previously_selected_cameras,
            )
    name = request.form['name']
    start = request.form['start']
    finish = request.form['finish']
    comment = request.form['comment']
    if finish:
        if start > finish:
            flash('Event start time is later than finish time.')
            return render_template('events/update.html', event=event)
    db.execute(
        'UPDATE event '
        'SET '
        '  name = COALESCE(?, name), '
        '  start = COALESCE(?, start), '
        '  finish = COALESCE(?, finish), '
        '  comment = COALESCE(?, comment) '
        'WHERE id = ?',
        (name, start, finish, comment, id_),
        )
    cameras_to_add = _get_cameras_from_form(request.form)
    cameras_to_delete = set(previously_selected_cameras).difference(set(cameras_to_add))
    _add_cameras_to_event(cameras_to_add, db, id_)
    _delete_cameras_from_event(cameras_to_delete, db, id_)
    db.commit()
    return redirect(url_for('index'))


@bp.route('/<string:id_>/delete', methods=('POST',))
@login_required
def delete(id_):
    _get_event(id_)
    db = get_db()
    db.execute('DELETE FROM event WHERE id = ?', (id_,))
    db.execute('DELETE FROM event_cameras WHERE event_id = ?', (id_,))
    db.commit()
    return redirect(url_for('index'))


@bp.route('/<string:id_>', methods=('GET',))
@login_required
def get(id_):
    mediaserver_api = current_app.config.get('MEDIASERVER_API')
    if mediaserver_api is None:
        flash("Mediaserver connection is required to update camera list. Please log in.")
        return redirect(url_for('auth.login'))
    webapp_port = current_app.config.get('WEBAPP_PORT')
    db = get_db()
    event_name = _get_event(id_)['name']
    cameras = _get_event_cameras_from_db(db, id_)
    return render_template(
        f'events/get.html',
        cameras=cameras,
        event_name=event_name,
        webapp_port=webapp_port,
    )


# TODO: Remove
@bp.route('/<string:event_id>/analytics_tracks', methods=('GET',), defaults={'camera_id': None})
@bp.route('/<string:event_id>/analytics_tracks/<string:camera_id>', methods=('GET',))
@login_required
def get_analytics_tracks(event_id, camera_id):
    mediaserver_api = current_app.config.get('MEDIASERVER_API')
    if mediaserver_api is None:
        flash("Mediaserver connection is required to update camera list. Please log in.")
        return redirect(url_for('auth.login'))
    db = get_db()
    event = _get_event(event_id)
    start_ms = event['start'].timestamp() * 1000
    finish_ms = event['finish'].timestamp() * 1000 if event['finish'] is not None else None
    all_event_cameras = _get_event_cameras_from_db(db, event_id)
    if camera_id is not None:
        if not camera_id in [camera.id for camera in all_event_cameras]:
            abort(404, f"Camera with ID {camera_id} not found among event {event['name']} cameras.")
        cameras = [camera for camera in all_event_cameras if camera.id == camera_id]
    else:
        cameras = _get_event_cameras_from_db(db, event_id)
    tracks = _get_analytics_tracks(mediaserver_api, start_ms, finish_ms, *cameras)
    return [track.to_json() for track in tracks]


@bp.route('/<string:event_id>/engagement', defaults={'camera_id': None, 'interval': 2}, methods=('GET',))
@bp.route('/<string:event_id>/engagement/<string:camera_id>', methods=('GET',), defaults={'interval': 2})
@login_required
def get_engagement_level(event_id, camera_id, interval):
    mediaserver_api = current_app.config.get('MEDIASERVER_API')
    if mediaserver_api is None:
        flash("Mediaserver connection is required to update camera list. Please log in.")
        return redirect(url_for('auth.login'))
    db = get_db()
    event = _get_event(event_id)
    finish = datetime.datetime.now()
    start = finish - timedelta(seconds=interval)
    start_timestamp = start.timestamp() * 1000
    finish_timestamp = finish.timestamp() * 1000
    all_event_cameras = _get_event_cameras_from_db(db, event_id)
    if camera_id is not None:
        if not camera_id in [camera.id for camera in all_event_cameras]:
            abort(404, f"Camera with ID {camera_id} not found among event {event['name']} cameras.")
        cameras = [camera for camera in all_event_cameras if camera.id == camera_id]
    else:
        cameras = _get_event_cameras_from_db(db, event_id)
    tracks = _get_analytics_tracks(mediaserver_api, start_timestamp, finish_timestamp, *cameras)
    score = calculate_average_engagement_rate(tracks)
    return {
        'timestamp': finish_timestamp,
        'value': int(score * 100),  # In percents
        }


def _get_event(id_, check_author=True):
    event = get_db().execute(
        'SELECT e.id, user_id, name, start, finish, comment, username'
        ' FROM event e JOIN user u ON e.user_id = u.id'
        ' WHERE e.id = ?',
        (id_,)).fetchone()
    if event is None:
        abort(404, f"Post id {id_} doesn't exist.")
    if check_author and event['user_id'] != g.user['id']:
        abort(403)
    return event


@bp.route('/camera_data/<string:camera_id_>', methods=('GET',), defaults={'unit': 'percent'})
def get_camera_data(camera_id_, unit):
    max_count = 50  # TODO: Make customizable
    db = get_db()
    raw_result = db.execute(
        'SELECT timestamp_, rate'
        ' FROM camera_engagement_rate'
        ' WHERE camera_id = ?',
        (camera_id_,)).fetchall()
    if len(raw_result) <= max_count:
        pass
    raw_result = raw_result[-max_count:]
    result = []
    for (timestamp_ms, rate) in raw_result:
        if unit == 'percent':
            rate *= 100
        result.append({'timestamp': datetime.datetime.fromtimestamp(timestamp_ms / 1000), 'value': rate})
    return jsonify(result)


class Camera:

    def __init__(self, raw: Mapping[str, Any]):
        self.id = format_uuid(raw['id'])
        self.name = raw['name']

    def as_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            }

    def __eq__(self, other):
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)


def _get_event_cameras_from_db(db, id_):
    raw_selected_cameras = db.execute(
        'SELECT c.id, c.name FROM camera c '
        ' JOIN event_cameras e ON c.id = e.camera_id '
        ' WHERE ? = e.event_id',
        (id_,)).fetchall()
    selected_cameras = [Camera(data) for data in raw_selected_cameras]
    return selected_cameras


def _get_cameras_from_form(form):
    camera_dicts_as_str = form.getlist('cameras')
    cameras = [Camera(json.loads(data.replace("'", '"'))) for data in camera_dicts_as_str]
    return cameras


def _add_cameras_to_event(cameras, db, event_id):
    query_placeholder = ','.join(['(?, ?)' for _ in range(len(cameras))])
    camera_values = []
    for camera in cameras:
        camera_values = [*camera_values, camera.id, camera.name]
    db.execute(
        'INSERT OR REPLACE INTO camera (id, name)'
        f' VALUES {query_placeholder}',
        camera_values,
    )
    event_cameras_values = []
    for camera in cameras:
        event_cameras_values = [*event_cameras_values, event_id, camera.id]
    db.execute(
        'INSERT OR REPLACE INTO event_cameras (event_id, camera_id)'
        f' VALUES {query_placeholder}',
        event_cameras_values,
        )


def _delete_cameras_from_event(cameras, db, event_id):
    event_cameras_values = [str((event_id, camera.id)) for camera in cameras]
    event_cameras_values_str = ','.join(event_cameras_values)
    db.execute(
        'DELETE FROM event_cameras'
        ' WHERE (event_id, camera_id) IN'
        f' ({event_cameras_values_str});')


def _get_all_cameras_from_db(db):
    raw_selected_cameras = db.execute('SELECT * FROM camera').fetchall()
    cameras = [Camera(data) for data in raw_selected_cameras]
    return cameras


def _get_mediaserver_cameras(mediaserver_api):
    raw_devices = mediaserver_api.list_devices()
    cameras = [Camera(data) for data in raw_devices if data['deviceType'] == 'Camera']
    return cameras


def _get_all_cameras(mediaserver_api, db):
    mediaserver_cameras = _get_mediaserver_cameras(mediaserver_api)
    # It is possible that some cameras were removed from the Mediaserver. But we might need the archived data for them.
    db_cameras = _get_all_cameras_from_db(db)
    return set(mediaserver_cameras).union(set(db_cameras))


def _get_analytics_tracks(mediaserver_api, start_ms, end_ms=None, *cameras: Camera):
    all_tracks = []
    params = {'start_time': start_ms}
    if end_ms is not None:
        params = {**params, 'end_time': end_ms}
    for camera in cameras:
        # TODO: Process camera non-existent case (e.g. deleted from Mediaserver)
        tracks = mediaserver_api.list_analytics_objects_tracks(camera_id=camera.id, **params)
        all_tracks = [*all_tracks, *tracks]
    return all_tracks
