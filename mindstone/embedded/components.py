# -*- coding: utf-8 -*-
""" Components module.

Resources:
    - https://servodatabase.com/servos/all
    - https://howtomechatronics.com/how-it-works/how-servo-motors-work-how-to-control-servos-using-arduino/
"""

import time
from abc import ABC, abstractmethod

from mindstone.core.utils import get_required_args

from .platforms.platform import current_platform


class ExecutableComponentABC(ABC):
    """ Executable Component Abstract Base Class.

    """

    def execute(self, operation: str, *args, **kwargs):
        try:
            getattr(self, operation)(*args, **kwargs)
        except (AttributeError, TypeError):
            raise RuntimeError("Operation '{}' for component '{}' does is invalid".format(
                operation, self.__class__.__name__))


class ReadableComponentABC(ABC):
    """ Readable Component Abstract Base Class.

    """

    @abstractmethod
    def read(self) -> dict:
        pass


class ComponentABC(ABC):
    """ Component Abstract Base Class.

    """

    def __init__(self):
        self.pins = {}

    def __del__(self):
        self.cleanup()

    def define_pin(self, pin_key: str, pin_id: int, pin_type: str, *args, **kwargs):
        self.pins[pin_key] = current_platform().new_channel(pin_id, pin_type, *args, **kwargs)

    def cleanup(self):
        for pin in self.pins.values():
            pin.cleanup()


class SwitchComponent(ComponentABC, ReadableComponentABC):
    """ Switch/Button Component Class.

    """

    def __init__(self, input_pin: int):
        super().__init__()
        self.define_pin("input", input_pin, "input")

    def read(self) -> dict:
        input_channel = self.pins["input"]
        return {
            "is_on": input_channel.value()
        }


class TriggerComponent(ComponentABC, ReadableComponentABC, ExecutableComponentABC):
    """ Trigger Component Class.

    """

    def __init__(self, trigger_pin: int, turn_on: bool = False):
        super().__init__()
        self.define_pin("trigger", trigger_pin, "output")
        if turn_on:
            self.turn_on()

    @property
    def is_on(self) -> bool:
        return self.pins["trigger"].state

    def read(self) -> dict:
        return {
            "is_on": self.is_on
        }

    def toggle(self):
        if self.is_on:
            self.turn_off()
        else:
            self.turn_on()

    def turn_on(self):
        self.pins["trigger"].high()

    def turn_off(self):
        self.pins["trigger"].low()


# trigger component aliases
LEDComponent = TriggerComponent
MotorComponent = TriggerComponent


class UltrasonicSensorComponent(ComponentABC, ReadableComponentABC):
    """ Ultrasonic Component Class.

    """

    def __init__(self, trigger_pin: int, echo_pin: int, trigger_pw: float = 0.00001, measurements: int = 1):
        super().__init__()

        self._trigger_pw = trigger_pw
        self._measurements = measurements

        self.define_pin("trigger", trigger_pin, "output")
        self.define_pin("echo", echo_pin, "input")

    def read(self) -> dict:
        time_change = self.measure_time_change()
        if self._measurements > 1:
            time_change = sum([self.measure_time_change()
                               for _ in range(self._measurements)]) / self._measurements
        return {
            "time_change": time_change
        }

    def measure_time_change(self) -> float:
        trigger_channel = self.pins["trigger"]
        echo_channel = self.pins["echo"]

        trigger_channel.low()

        # create a short delay for the sensor to settle
        time.sleep(0.1)

        # request a pulse to the sensor's activate pin
        trigger_channel.high()
        time.sleep(self._trigger_pw)
        trigger_channel.low()

        # measure time for echo to return to receiver
        while not echo_channel.value():
            pass
        initial_time = time.time()
        while echo_channel.value():
            pass
        final_time = time.time()

        return final_time - initial_time


class ServoComponent(ComponentABC, ExecutableComponentABC, ReadableComponentABC):
    """ Servo Component Class.

    Some specifications:
        Tower Pro SG90 (default):
            frequency=50,
            start_on_time=.5 * 10 ** -3
            end_on_time=2.5 * 10 ** -3
            max_angle=180
    """

    def __init__(self, trigger_pin: int, frequency: float = 50, start_on_time: float = 0.0005,
                 end_on_time: float = 0.0025, max_angle: float = 180):
        super().__init__()
        self._is_active = False
        self._angle = None
        self._frequency = frequency
        self._start_on_time = start_on_time
        self._end_on_time = end_on_time
        self._max_angle = max_angle

        self.define_pin("trigger", trigger_pin, "pwm", frequency=frequency)

    def read(self) -> dict:
        return {
            "angle": self._angle,
            "is_active": self._is_active
        }

    def change_angle(self, angle: float) -> None:
        if not self._is_active:
            raise RuntimeWarning("Could not set angle. Servo can't be used without first being activated.")
        if not 0 <= angle <= self._max_angle:
            raise RuntimeWarning("Servo angle should be between 0 and {}".format(self._max_angle))
        self._angle = angle
        self.pins["trigger"].change_duty_cycle(self._angle_to_duty_cycle(angle))

    def start(self, angle: float = 0) -> None:
        dc = self._angle_to_duty_cycle(angle)
        self.pins["trigger"].start(dc)
        self._is_active = True

    def stop(self) -> None:
        self.pins["trigger"].stop()
        self._is_active = False

    def _angle_to_duty_cycle(self, angle: float) -> float:
        time_delta = self._end_on_time - self._start_on_time
        return round(self._frequency * 100 * (self._start_on_time + time_delta * angle / self._max_angle), 2)


supported_components = {
    "led": LEDComponent,
    "motor": MotorComponent,
    "servo": ServoComponent,
    "switch": SwitchComponent,
    "trigger": TriggerComponent,
    "ultrasonic": UltrasonicSensorComponent
}

required_setup_args = {
    key: get_required_args(component.__init__).difference({"self"}) for key, component in supported_components.items()
}
