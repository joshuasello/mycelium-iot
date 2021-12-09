# -*- coding: utf-8 -*-
""" Connection Subpackage.

The connection subpackage holds classes that handle the communication
between the driver and the controller.
"""

from .tcp import TCPClient, TCPServer

server_types = {
    "tcp": TCPServer
}

client_types = {
    "tcp": TCPClient
}
