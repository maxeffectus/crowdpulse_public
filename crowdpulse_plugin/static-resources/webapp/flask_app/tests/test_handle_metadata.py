import unittest

from flask_app.flaskr.handle_metadata import process_plugin_metadata_track, calculate_engagement
from flask_app.tests._plugin_metadata_sample import metadata_sample


class TestPluginMetadataHandling(unittest.TestCase):

    def test_process_plugin_metadata(self):
        expected_result = [
            (0.5, '00000000-0000-0000-0000-000000000001'),
            (0.0, '00000000-0000-0000-0000-000000000002'),
            ]
        engagement_snapshots = []
        for raw_track in metadata_sample:
            engagement_snapshots.append(process_plugin_metadata_track(raw_track))
        actual_result = calculate_engagement(engagement_snapshots)
        self.assertListEqual(expected_result, actual_result)
