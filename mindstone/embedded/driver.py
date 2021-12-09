# -*- coding: utf-8 -*-
""" Driver Implementation.

The driver acts an interface between the controller and the platform it runs on.
When activated, the driver starts a server to host incoming requests from controllers.

NOTE: Only one driver can operate on a device during the runtime of the program.

Example:
    from mindstone import driver

    if __name__ == '__main__':
        driver.run(platform="dummy")
"""

import threading
import time
from abc import ABC, abstractmethod

from mindstone.core.connection import server_types
from mindstone.core.transactions import Transaction
from mindstone.core.utils import TerminalColors

from .components import supported_components, ExecutableComponentABC, ReadableComponentABC
from .platforms import supported_platforms


class DriverABC(ABC):
    """ Driver abstract base class.

    """

    @abstractmethod
    def create_routine(self, name: str, interval: float, entity: str, executor: str, operation: str,
                       kwargs: dict):
        pass

    @abstractmethod
    def create_component(self, name: str, type: str, **setup):
        pass

    @abstractmethod
    def delete_routine(self, name: str):
        pass

    @abstractmethod
    def delete_component(self, name: str):
        pass

    @abstractmethod
    def execute_component(self, name: str, operation: str, **kwargs):
        pass

    @abstractmethod
    def get(self, *fields):
        pass


class _RoutinesThread(threading.Thread):
    """ Routines thread class.

    """

    def __init__(self):
        super(_RoutinesThread, self).__init__()
        self.is_running = False

    def run(self):
        self.is_running = True
        time.sleep(time.time() * 1000 % 1 / 1000)  # enable to sync clock
        start_time = time.time()
        to_update = {}

        while self.is_running:
            # in case a subroutine is later on removed later on in the program
            # delete any entries from the update register that are no longer in use
            # REVIEW: What?!
            for key in _driver.routines.keys():
                if key not in _driver.routines.keys():
                    del to_update[key]

            for key, value in _driver.routines.items():
                if key not in to_update:
                    to_update[key] = False
                entity, executor, operation, kwargs, time_interval = value
                # time should be considered accurate to the millisecond (3 decimal places)
                current_time = time.time()
                interval_mod = round((current_time - start_time) % time_interval)
                # to prevent issues with accuracies concerning time measurement, the equation
                # used is rounded to the nearest whole number. This caused another problem,
                # causing multiple updates in the time interval. This implementation makes it
                # so that the coordinator parameter_states associated with a given subroutine is only updated
                # once in the interval.
                if not to_update[key] and interval_mod == 0:
                    _request_handlers["exe"](entity, executor, operation, kwargs)
                    to_update[key] = True
                elif interval_mod != 0:
                    to_update[key] = False
            time.sleep(.001 - time.time() * 1000 % 1 / 1000)


class _Driver(DriverABC):

    def __init__(self):
        self.components = {}
        self.routines = {}
        self._entity_lookup = {
            "component": self.components.keys,
            "routine": self.routines.keys
        }
        self._get_handlers = {
            "states": self.get_states,
            "components": self.get_components,
            "routines": self.get_routines
        }

    def create_routine(self, name: str, interval: float, entity: str, executor: str, operation: str,
                       kwargs: dict) -> None:
        if entity in _exe_handlers and executor not in self._entity_lookup[entity]():
            raise RuntimeError("Executor component '{}' could not be found.".format(executor))
        self.routines[name] = (entity, executor, operation, kwargs, interval)

    def create_component(self, name: str, type: str, setup: dict = None) -> None:
        setup = setup if setup is not None else {}
        # NOTE: Any existing component with the same name will be deleted and replaced.
        # initialize a new component at the key 'name'
        self.components[name] = supported_components[type](**setup)

    def delete_routine(self, name: str) -> None:
        if name in self.routines:
            del self.routines[name]

    def delete_component(self, name: str) -> None:
        if name in self.components:
            del self.components[name]

    def execute_component(self, name: str, operation: str, kwargs: dict = None) -> None:
        kwargs = kwargs if kwargs is not None else {}
        if name not in self.components:
            raise RuntimeError("Component '{}' has not been registered.".format(name))
        component = self.components[name]
        if not isinstance(component, ExecutableComponentABC):
            raise RuntimeError("Component '{}' is not executable.".format(name))
        component.execute(operation, **kwargs)

    def get(self, fields: list) -> dict:
        return {field: self._get_handlers[field]() for field in fields}

    def get_routines(self) -> list:
        return list(self.routines.keys())

    def get_components(self) -> list:
        return list(self.components.keys())

    def get_states(self) -> dict:
        return {
            name: component.read()
            for name, component in self.components.items()
            if isinstance(component, ReadableComponentABC)
        }


def _handle_received_data(received: list) -> dict:
    response = {}
    for method, kwargs in received:
        display("\tHANDLED METHOD '{}'".format(TerminalColors.OKBLUE + method + TerminalColors.ENDC))
        display(_items_to_str(item_prefix="\t\t", **kwargs))
        result = _request_handlers[method](**kwargs)
        if method in retrieval_methods and result is not None:
            response.update(result)
    return response


def _on_receive(received: bytes, client_address: tuple = None) -> bytes:
    """ Handles an incoming request from the controller.

    :param received: ata sent by the controller
    :param client_address: The address of the client sending the request
    :return: None
    """
    error_message = None

    # ~ get the time that this request was handled
    feedback_to_send = Transaction("server", received_time=time.time())

    try:
        display(TerminalColors.OKGREEN + "[{}] RECEIVED REQUEST from {}".format(
            time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(feedback_to_send["received_time"])),
            client_address
        ) + TerminalColors.ENDC)

        # ~ extract the data from the request.
        received = Transaction.decode("client", received)
        # ~ handle the received data.
        feedback_to_send["response"] = _handle_received_data(received["input"])
    except (RuntimeError, RuntimeWarning, ValueError) as e:
        # if the drive fails to process teh data then report the error back to the
        # controller instead of terminating the driver.
        error_message = "{}: {}".format(e.__class__.__name__, str(e))
        display(TerminalColors.FAIL + "\t!!! " + error_message + TerminalColors.ENDC)

    # ~ prepare the message to be sent
    feedback_to_send["error"] = error_message
    feedback_to_send["sent_time"] = time.time()

    # ~ finally, return the result of the the processing done by the driver
    encoded = feedback_to_send.encoded()

    display(TerminalColors.OKGREEN + "[{}] RESPONSE SENT".format(
        time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(feedback_to_send["sent_time"])),
    ) + TerminalColors.ENDC)

    return encoded


def _items_to_str(item_prefix: str = "", **kwargs):
    return "".join(item_prefix + "{}: {}\n".format(*item) for item in kwargs.items()).strip("\n")


def set_verbosity(verbose: bool):
    """ sets the verbosity of the driver system. """
    global _verbose
    _verbose = verbose


def display(*args, **kwargs):
    if _verbose:
        print(*args, **kwargs)


def run(platform: str, port: int = 50000, connection_type: str = "tcp", verbose: bool = True, *args, **kwargs):
    """ Start the driver.

    :param platform: The platform used by the driver.
    :param port: The connection port used by the driver's server.
    :param connection_type: The type of connection used.
    :param verbose: If the output of processes should be displayed in the console.
    :param args: Positional arguments for setting up the platform (differs depending on the platform).
    :param kwargs: Key-word arguments for setting up the platform (differs depending on the platform).
    :return: None
    """
    # setup platform
    supported_platforms[platform](*args, **kwargs)

    # set the global verbosity setting
    set_verbosity(verbose)

    # start the routines thread
    _routines.start()

    # start the connection server so that controllers can connect to
    # this driver.
    display("{}STARTING SERVER @ ({}){}".format(TerminalColors.HEADER, port, TerminalColors.ENDC))
    display("Press CTRL+C to end the server.")
    display("-" * 50)

    server_types[connection_type].serve(hostname="", port=port, on_receive=_on_receive)


_driver = _Driver()

_routines = _RoutinesThread()

_verbose = True

# noinspection PyArgumentList
_request_handlers = {
    "get": _driver.get,
    "exe": lambda entity, name, operation, kwargs=None: _exe_handlers[entity](name, operation, kwargs),
    "delete": lambda entity, name: _delete_handlers[entity](name),
    "create": lambda entity, data: _create_handlers[entity](**data)
}

_create_handlers = {
    "routine": _driver.create_routine,
    "component": _driver.create_component
}

_exe_handlers = {
    "component": _driver.execute_component
}

_delete_handlers = {
    "component": _driver.delete_component,
    "routine": _driver.delete_routine
}

retrieval_methods = {"get"}
