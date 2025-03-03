import argparse
import logging

_logger = logging.getLogger(__name__)


import sys

from . import create_app


def _parse_args(args):
    parser = argparse.ArgumentParser()
    parser.add_argument('--crowdpulse-plugin-port', type=int, required=True)
    parser.add_argument('--mediaserver-port', type=int, default=7001)
    parser.add_argument('--web-app-port', type=int, default=5000)
    return parser.parse_args(args)


if __name__ == '__main__':
    parsed_args = _parse_args(sys.argv[1:])
    # TODO: Make log level customizable
    logging.basicConfig(filename='webapp.log', level=logging.DEBUG)
    _logger.info(
        "Starting webapp on port %d with Mediaserver port %d and CrowdPulse plugin port %d",
        parsed_args.web_app_port, parsed_args.mediaserver_port, parsed_args.crowdpulse_plugin_port)
    app = create_app(
        config={
            'CROWDPULSE_PLUGIN_PORT': parsed_args.crowdpulse_plugin_port,
            'MEDIASERVER_PORT': parsed_args.mediaserver_port,
            'WEBAPP_PORT': parsed_args.web_app_port,
            'RANDOM_CAMERA_DATA': {},
            'TRACK_ENGAGEMENT_BUFFER': [],
            })
    app.run(debug=True, port=parsed_args.web_app_port)
