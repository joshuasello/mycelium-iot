# -*- coding: utf-8 -*-
""" Server Module.

"""

from abc import ABC, abstractmethod
from collections.abc import Callable


class ServerABC(ABC):
    """ Server Abstract Base Class.

    """

    def __str__(self) -> str:
        return "{}()".format(self.__class__.__name__)

    @staticmethod
    @abstractmethod
    def serve(hostname: str, port: int, on_receive: Callable) -> None:
        pass
