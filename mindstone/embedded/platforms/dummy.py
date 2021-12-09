# -*- coding: utf-8 -*-
""" Dummy Platform Implementation.

The dummy platform exists for testing purposes. When a component interfaces with it, it will
print out channels t used. This is useful for debugging

"""

from mindstone.embedded.pins import OutputPinABC, PWMPinABC

from .platform import PlatformABC


class OutputPin(OutputPinABC):
    """ Output Pin Class.

    """

    LOW = False
    HIGH = True

    def __init__(self, pin_id: int):
        super(OutputPin, self).__init__(pin_id)
        print("NEW OUTPUT PIN (id={})".format(pin_id))
        self._state = False

    @property
    def state(self) -> bool:
        return self._state

    def high(self):
        self._state = self.HIGH
        print("OUTPUT PIN SET (id={}, state={})".format(self.id, self._state))

    def low(self):
        self._state = self.LOW
        print("OUTPUT PIN SET (id={}, state={})".format(self.id, self._state))

    def cleanup(self):
        print("CLEANED OUTPUT PIN (id={})".format(self.id))


class PWMPin(PWMPinABC):
    """ Dummy Pulse Width Modulation Pin Class.

    """

    def __init__(self, pin_id: int, frequency: float):
        super(PWMPin, self).__init__(pin_id, frequency)
        print("NEW PWM PIN (id={}, frequency={})".format(pin_id, frequency))

    def start(self, duty_cycle: float):
        self.duty_cycle = duty_cycle
        print("START PWM PIN (id={}, dc={})".format(self.id, self.duty_cycle))

    def stop(self):
        print("STOP PWM PIN (id={}, dc={})".format(self.id, self.duty_cycle))

    def change_frequency(self, frequency: float):
        self.frequency = frequency
        print("CHANGED PWM PIN FREQUENCY (id={}, frequency={})".format(self.id, frequency))

    def change_duty_cycle(self, duty_cycle: float):
        self.duty_cycle = duty_cycle
        print("CHANGED PWM PIN DUTY CYCLE (id={}, dc={})".format(self.id, duty_cycle))

    def cleanup(self):
        print("CLEANED PWM PIN (id={})".format(self.id))


class Platform(PlatformABC):
    """ Dummy Platform Class.

    """

    channel_types = {
        "output": OutputPin,
        "pwm": PWMPin
    }
