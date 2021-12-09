# -*- coding: utf-8 -*-
""" Platform Implementation Module.

A platform is an object that stores components capable of interfacing with the device the program
runs on. When the driver is running on a raspberry py platform, it uses the platform object to interface
with the GPIO pins.
"""

from abc import ABC

from mindstone.embedded.pins import PinABC


class PlatformABC(ABC, dict):
    """ Platform Abstract Base Class.

    """

    channel_types: dict = None

    def __init__(self):
        assert self.channel_types is not None, \
            "Channel types for platform have not been defined."

        super(PlatformABC, self).__init__()

        _define_current_platform(self)

    def trigger(self, channel_id: int, method_name: str, *args, **kwargs):
        return getattr(self[channel_id], method_name)(*args, **kwargs)

    def new_channel(self, channel_id: int, type: str, *args, **kwargs) -> PinABC:
        self[channel_id] = self.channel_types[type](channel_id, *args, **kwargs)
        return self[channel_id]

    def cleanup(self):
        pass


_current = None


def platform_is_set() -> bool:
    return isinstance(_current, PlatformABC)


def current_platform() -> PlatformABC:
    if not platform_is_set():
        raise NotImplementedError("Platform has not been set.")
    return _current


def _define_current_platform(platform: PlatformABC):
    global _current
    if platform_is_set():
        raise Exception("More than one platform can't be set.")
    # assign to global current platform
    _current = platform
