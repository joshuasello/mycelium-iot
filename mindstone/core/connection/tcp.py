# -*- coding: utf-8 -*-
""" TCP Connection module.

Resources:
    - https://docs.python.org/3/library/socketserver.html
    - https://docs.python.org/3/howto/sockets.html
"""

import socket
import socketserver
from collections.abc import Callable

from .client import ClientABC
from .server import ServerABC

get_hostname: Callable = socket.gethostname

# prevents OSError: [Errno 98] Address already in use
socketserver.TCPServer.allow_reuse_address = True


def get_host_ip() -> str:
    return socket.gethostbyname(get_hostname())


class TCPServer(ServerABC):
    """ tcp server class.

    """

    @staticmethod
    def serve(hostname: str, port: int, on_receive: Callable) -> None:
        _TCPRequestHandler.request_handler = on_receive
        with socketserver.TCPServer((hostname, port), _TCPRequestHandler) as server:
            # Activate the server; this will keep running until the user
            # interrupts the program with Ctrl-C
            server.serve_forever()


class TCPClient(ClientABC):
    """ TCP client class.

    """

    def send(self, data: bytes) -> bytes:
        # 1. create a socket (SOCK_STREAM means a TCP socket)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            # 2. connect to server and request data
            # TODO: Fix OSError: [WinError 10048] Only one usage of each socket address
            #  (protocol/network address/port) is normally permitted
            sock.connect((self.target_hostname, self.target_port))
            sock.send(data)

            # 3. receive data from the server and shut down
            received = sock.recv(1024)

        return received


class _TCPRequestHandler(socketserver.BaseRequestHandler):
    """ tcp request handler class.

    """

    request_handler: Callable = None

    def handle(self) -> None:
        # 1. receive the data from the client
        # self.request is the TCP socket connected to the client
        received = self.request.recv(1024).strip()
        # 2. using the request handler callable, process that data
        # and retrieve the data that should be sent back to the client
        to_send = _TCPRequestHandler.request_handler(received, self.client_address)
        # 3. finally, request the data back to the client.
        self.request.sendall(to_send)
