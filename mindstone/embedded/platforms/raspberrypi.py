# -*- coding: utf-8 -*-
""" Raspberry Pi Platform Implementation.

Pin types:
    1. Input Pin
    2. Output Pin
    3. PWM Pin

NOTE: Unless the program is running on a raspberry pi,
    this module when imported will raise an ImportError.
    This should be handled appropriately

Installing RPi.GPIO Manually:
    $ cd ~
    $ wget https://pypi.python.org/packages/source/R/RPi.GPIO/RPi.GPIO-0.5.11.tar.gz
    $ tar -xvf RPi.GPIO-0.5.11.tar.gz
    $ cd RPi.GPIO-0.5.11
    $ sudo python setup.py install
    $ cd ~
    $ sudo rm -rf RPi.GPIO-0.*

Installing a new version of python on Raspbian
Source: https://installvirtual.com/how-to-install-python-3-8-on-raspberry-pi-raspbian/
1. Update the Raspbian
    $ sudo apt-get update
2. Prerequisites
    $ sudo apt-get install -y build-essential tk-dev libncurses5-dev libncursesw5-dev libreadline6-dev libdb5.3-dev
        libgdbm-dev libsqlite3-dev libssl-dev libbz2-dev libexpat1-dev liblzma-dev zlib1g-dev libffi-dev tar
        wget vim
3. Download Python
    $ wget https://www.python.org/ftp/python/3.8.0/Python-3.8.0.tgz
4. Install Python 3.8
    $ sudo tar zxf Python-3.8.0.tgz
    $ cd Python-3.8.0
    $ sudo ./configure --enable-optimizations
    $ sudo make -j 4
    $ sudo make altinstall
5. Check Python version
    $ python3.8 -V
6. Make Python 3.8 as the default version
    $ echo "alias python=/usr/local/bin/python3.8" >> ~/.bashrc
    $ source ~/.bashrc
7. Check Python Version
    $ python -V
    $ Python 3.8.0

Methods for handling switch debounce:
    Switch debounce occurs when an input registers an event more that once per activate.
     - add a 0.1uF capacitor across your switch.
     - software debouncing
     - a combination of both


Resources:
 - https://sourceforge.net/p/raspberry-gpio-python/wiki/Inputs/
 - https://sourceforge.net/p/raspberry-gpio-python/wiki/PWM/
 - https://sourceforge.net/p/raspberry-gpio-python/wiki/Outputs/

"""

try:
    import RPi.GPIO
except RuntimeError:
    print("Error importing RPi.GPIO!  This is probably because"
          " you need superuser privileges.  You can achieve this"
          " by using 'sudo' to run your script")
from collections.abc import Callable

from mindstone.embedded.pins import InputPinABC, OutputPinABC, PWMPinABC
from mindstone.embedded.platforms.platform import PlatformABC

GPIO = RPi.GPIO


class InputPin(InputPinABC):
    """ Raspberry Pi Input Pin Class.

    """

    LOW = GPIO.LOW
    HIGH = GPIO.HIGH
    PULL_UP = GPIO.PUD_UP
    PULL_DOWN = GPIO.PUD_DOWN
    RISING = GPIO.RISING
    FALLING = GPIO.FALLING
    BOTH = GPIO.BOTH

    def __init__(self, pin_id: int, pull=None):
        super(InputPin, self).__init__(pin_id)
        if pull is None:
            # this means that the value that is read by the input is undefined
            # until it receives a signal
            GPIO.setup(pin_id, GPIO.IN)
        else:
            GPIO.setup(pin_id, GPIO.IN, pull_up_down=pull)

    def value(self) -> bool:
        return GPIO.input(self.id) == self.HIGH

    def wait_for_edge(self, edge_type, *args, **kwargs):
        GPIO.wait_for_edge(self.id, edge_type, *args, **kwargs)

    def event(self, edge_type, *args, **kwargs):
        GPIO.add_event_detect(self.id, edge_type, *args, **kwargs)

    def remove_event(self):
        GPIO.remove_event_detect(self.id)

    def event_callback(self, callback: Callable, *args, **kwargs):
        GPIO.add_event_callback(self.id, callback, *args, **kwargs)

    def event_detected(self) -> bool:
        return GPIO.event_detected(self.id)

    def cleanup(self) -> None:
        GPIO.cleanup(self.id)


class OutputPin(OutputPinABC):
    """ Raspberry Pi Output Pin Class.

    """

    LOW = GPIO.LOW
    HIGH = GPIO.HIGH

    def __init__(self, pin_id: int):
        super().__init__(pin_id)
        GPIO.setup(pin_id, GPIO.OUT)

    @property
    def state(self) -> bool:
        return bool(GPIO.input(self.id))

    def high(self) -> None:
        GPIO.output(self.id, self.HIGH)

    def low(self) -> None:
        GPIO.output(self.id, self.LOW)

    def cleanup(self) -> None:
        GPIO.cleanup(self.id)


class PWMPin(PWMPinABC):
    """ Raspberry Pi Pulse Width Modulation Pin Class.

    """

    def __init__(self, pin_id: int, frequency: float):
        super(PWMPin, self).__init__(pin_id, frequency)
        # 1. the channel needs to be set to an output before
        # it can be used as a pwm channel
        GPIO.setup(pin_id, GPIO.OUT)
        # 2. store a pwm variable that can be later used
        self.pwm = GPIO.PWM(pin_id, frequency)

    def start(self, duty_cycle: float) -> None:
        self.pwm.start(duty_cycle)
        self.duty_cycle = duty_cycle

    def stop(self) -> None:
        self.pwm.stop()

    def change_frequency(self, frequency: float) -> None:
        self.pwm.ChangeFrequency(frequency)
        self.frequency = frequency

    def change_duty_cycle(self, duty_cycle: float) -> None:
        self.pwm.ChangeDutyCycle(duty_cycle)
        self.duty_cycle = duty_cycle

    def cleanup(self) -> None:
        self.stop()
        GPIO.cleanup(self.id)


class Platform(PlatformABC):
    """ Raspberry Pi Platform Class.

    """
    channel_types = {
        "input": InputPin,
        "output": OutputPin,
        "pwm": PWMPin
    }

    def __init__(self, mode: str = "bcm", warnings: bool = False):
        super().__init__()
        if mode == "board":
            GPIO.setmode(GPIO.BOARD)
        elif mode == "bcm":
            GPIO.setmode(GPIO.BCM)
        else:
            RuntimeError("The provided board mode is invalid. try 'board' or 'bcm'")
        GPIO.setwarnings(warnings)

    def cleanup(self) -> None:
        for channel in self.values():
            channel.clean()
