# -*- coding: utf-8 -*-
""" Client Module.

"""

from abc import ABC, abstractmethod


class ClientABC(ABC):
    """ Client Abstract Base Class.

    """

    def __init__(self, target_hostname: str, target_port: int):
        self.target_hostname = target_hostname
        self.target_port = target_port

    def __str__(self) -> str:
        return "{}(target_hostname={}, target_port={})".format(self.__class__.__name__,
                                                               self.target_hostname, self.target_port)

    @property
    def target_address(self) -> tuple:
        return self.target_hostname, self.target_port

    @abstractmethod
    def send(self, data: bytes) -> bytes:
        pass
