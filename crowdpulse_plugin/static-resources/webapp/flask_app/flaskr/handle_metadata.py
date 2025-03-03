import logging
from statistics import mean
from typing import Collection, Mapping, Any

from flask import Blueprint, request, Response, current_app

from .common import format_uuid
from .db import get_db
from .engagement_threshold import get_threshold_value_from_db
from .http.api.mediaserver import AnalyticsTrack

_logger = logging.getLogger(__name__)


bp = Blueprint('handle_metadata', __name__, url_prefix='/metadata')


@bp.route('/', methods=('POST',))
def handle_metadata():
    flush_interval_ms = 2000
    buffer = current_app.config['TRACK_ENGAGEMENT_BUFFER']
    plugin_metadata = request.json
    _logger.debug("Got plugin metadata for track: %s", plugin_metadata)
    track_engagement = process_plugin_metadata_track(plugin_metadata)
    _logger.debug("Calculated track_engagement: %s", track_engagement)
    if track_engagement is None:
        return Response(status=200)
    current_app.config['TRACK_ENGAGEMENT_BUFFER'].append(track_engagement)
    [first_track_timestamp_ms, _, _] = buffer[0]
    [current_track_timestamp_ms, _, _] = track_engagement
    if current_track_timestamp_ms - first_track_timestamp_ms >= flush_interval_ms:
        engagement_per_camera = calculate_engagement(buffer)
        db = get_db()
        for record in engagement_per_camera:
            db.execute(
                'INSERT INTO camera_engagement_rate (timestamp_, rate, camera_id)'
                ' VALUES (?, ?, ?)',
                (first_track_timestamp_ms, *record),
                )
            [camera_engagement_rate, camera_id] = record
            thresh_val = get_threshold_value_from_db(db, camera_id=camera_id)
            if camera_engagement_rate < thresh_val:
                plugin_api = current_app.config['PLUGIN_API']
                plugin_api.send_analytics_event(
                    type_='tigre.engagementBelowLevel',
                    camera_id=camera_id,
                    caption="ENGAGEMENT LEVEL DROP!",
                    description=f"Engagement level on camera is below the threshold {thresh_val * 100:.1f}%",
                    attributes={
                        'camera_id': camera_id,
                        'threshold': thresh_val,
                        }
                    )
        db.commit()
        current_app.config.from_mapping({'TRACK_ENGAGEMENT_BUFFER': []})
        _logger.info(
            "Recorded engagement stats to DB, (timestamp_ms, rate, camera_id): %s. "
            "TRACK_ENGAGEMENT_BUFFER flushed.", engagement_per_camera)
    return Response(status=200)


class TrackTypeIds:

    ATTENTIVE = 'nx.nxai.Attentive'
    DISTRACTED = 'nx.nxai.Distracted'


def calculate_average_engagement_rate(tracks: Collection[AnalyticsTrack]) -> float:
    # TODO: Improve heuristics
    if len(tracks) == 0:
        return 0
    attentive_tracks = [t for t in tracks if t.type_id == TrackTypeIds.ATTENTIVE]
    score = float(len(attentive_tracks)) / len(tracks)
    return score


class _MetadataTrack:
    def __init__(self, raw_track: Mapping[str, Any]):
        self._raw_track = raw_track

    def camera_id(self):
        return format_uuid(self._raw_track['deviceId'])

    def timestamp_us(self):
        return int(self._raw_track['timestampUs'])

    def type_id(self):
        return self._raw_track['objectMetadataList'][0]['typeId']


def process_plugin_metadata_track(raw_track):
    track = _MetadataTrack(raw_track)
    type_id = track.type_id()
    if type_id not in (TrackTypeIds.ATTENTIVE, TrackTypeIds.DISTRACTED):
        return None
    rate = 1.0 if track.type_id() == TrackTypeIds.ATTENTIVE else 0.0
    timestamp_ms = track.timestamp_us() // 1000
    camera_id = track.camera_id()
    return timestamp_ms, rate, camera_id


def calculate_engagement(track_engagement_rates):
    raw_result = {}
    for engagement_data in track_engagement_rates:
        if engagement_data is None:
            continue
        (timestamp_ms, rate, camera_id) = engagement_data
        camera_rates = raw_result.setdefault(camera_id, [])
        camera_rates.append(rate)
    engagement_rates = [(mean(rates), camera_id) for camera_id, rates in raw_result.items()]
    return engagement_rates
