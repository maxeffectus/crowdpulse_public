from flask import Blueprint, request, jsonify, Response

from .auth import login_required
from .db import get_db

bp = Blueprint('engagement_threshold', __name__, url_prefix='/engagement_threshold')


@bp.route('/<string:camera_id>', methods=('GET', 'POST'), defaults={'unit': 'percent'})
@login_required
def process_engagement_threshold(camera_id, unit):
    db = get_db()
    if request.method == 'GET':
        value = get_threshold_value_from_db(db, camera_id)
        if unit == 'percent':
            return_value = value * 100
        else:
            return_value = value
        return jsonify({'engagement_threshold': return_value})
    thresh_data = request.json
    if 'threshold' not in thresh_data:
        return Response(status=400)
    threshold = thresh_data['threshold']
    if unit == 'percent':
        threshold = threshold / 100
    if not 0.0 <= threshold <= 1.0:
        return Response(status=422)
    db.execute(
        'UPDATE camera'
        ' SET threshold = COALESCE(?, threshold)'
        ' WHERE id = ?',
        (threshold, camera_id)
        )
    db.commit()
    return Response(status=200)


def get_threshold_value_from_db(db, camera_id):
    camera_row = db.execute(
        'SELECT threshold FROM camera WHERE id = ?',
        (camera_id,)).fetchone()
    return camera_row['threshold']
