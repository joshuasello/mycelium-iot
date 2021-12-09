# -*- coding: utf-8 -*-
""" Pin Types.

"""

from abc import ABC, abstractmethod
from collections.abc import Callable


class PinABC(ABC):
    """ Pin Abstract Base Class.

    """

    def __init__(self, pin_id: int):
        self.id = pin_id

    @abstractmethod
    def cleanup(self):
        pass


class OutputPinABC(PinABC, ABC):
    """ Output Pin Abstract Base Class.

    """

    LOW = None
    HIGH = None

    @property
    @abstractmethod
    def state(self) -> bool:
        pass

    @abstractmethod
    def high(self):
        pass

    @abstractmethod
    def low(self):
        pass


class InputPinABC(PinABC, ABC):
    """ Input pin abstract base class.

    """

    LOW = None
    HIGH = None
    PULL_UP = None
    PULL_DOWN = None
    RISING = None
    FALLING = None
    BOTH = None

    @abstractmethod
    def value(self) -> bool:
        """Input value."""
        pass

    @abstractmethod
    def wait_for_edge(self, edge_type, timeout: int = None):
        """Blocks the execution of the program until an edge is detected"""
        pass

    @abstractmethod
    def event(self, edge_type, callback: Callable = None, bounce_time: int = None):
        pass

    @abstractmethod
    def remove_event(self):
        pass

    @abstractmethod
    def event_callback(self, callback: Callable, bounce_time: int = None):
        pass

    @abstractmethod
    def event_detected(self) -> bool:
        pass


class PWMPinABC(PinABC, ABC):
    """ Pulse width modulation (PWM) pin abstract base class.

    """

    LOW = None
    HIGH = None

    def __init__(self, pin_id: int, frequency: float):
        self.frequency = frequency
        self.duty_cycle = None
        # the attributes above may be used to set up this channel
        # this means that the super class should be initialized after
        # they are defined.
        super().__init__(pin_id)

    @abstractmethod
    def start(self, duty_cycle: float):
        pass

    @abstractmethod
    def stop(self):
        pass

    @abstractmethod
    def change_frequency(self, frequency: float):
        pass

    @abstractmethod
    def change_duty_cycle(self, duty_cycle: float):
        pass
