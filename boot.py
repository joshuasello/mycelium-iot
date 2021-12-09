#!/usr/bin/env python
""" mindstone driver starter.

"""

import argparse

from mindstone import __version__
from mindstone import driver


parser = argparse.ArgumentParser(
    prog="mindstone driver boot script.",
    description='Initialize a new driver.'
)
parser.version = __version__

parser.add_argument(
    "--platform",
    action="store",
    type=str,
    help="The platform the driver is running on.",
    required=True
)
parser.add_argument(
    "--port",
    action="store",
    type=int,
    help="The driver's connection port.",
    default=50000
)
parser.add_argument(
    "--conntype",
    action="store",
    type=str,
    help="The type of connection used by the driver.",
    default="tcp"
)
parser.add_argument(
    "-v",
    "--verbose",
    action="store_true",
    help="Sets the verbosity of the operation."
)
parser.add_argument(
    "-V",
    "--version",
    action="version",
    help="Gets the current running version of mindstone."
)

args = parser.parse_args()


if __name__ == '__main__':
    driver.run(
        port=args.port,
        connection_type=args.conntype,
        platform=args.platform,
        verbose=args.verbose
    )
