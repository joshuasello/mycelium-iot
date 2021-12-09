# -*- coding: utf-8 -*-
""" Controller to Driver Interface.

"""

from mindstone.core.transactions import Transaction
from mindstone.embedded.driver import DriverABC


class RequestsWrapper(DriverABC):

    def __init__(self):
        self.requests = []

    def request(self, method: str, **kwargs) -> None:
        self.requests.append((method.lower().strip(), kwargs))

    def create_routine(self, name: str, interval: float, entity: str, executor: str, operation: str, **kwargs):
        self.request(method="create", entity="routine", data={
            "name": name,
            "interval": interval,
            "entity": entity,
            "executor": executor,
            "operation": operation,
            "kwargs": kwargs
        })
        return self

    def create_component(self, name: str, type: str, **setup):
        self.request(method="create", entity="component", data={"name": name, "type": type, "setup": setup})
        return self

    def delete_routine(self, name: str):
        self.request(method="delete", entity="routine", name=name)
        return self

    def delete_component(self, name: str):
        self.request(method="delete", entity="component", name=name)
        return self

    def execute_component(self, name: str, operation: str, **kwargs):
        self.request(method="exe", entity="component", name=name, operation=operation, kwargs=kwargs)
        return self

    def get(self, *fields):
        self.request(method="get", fields=fields)
        return self


class DriverInterface(RequestsWrapper):

    def __init__(self):
        super(DriverInterface, self).__init__()
        self.client = None

    def request(self, method: str, **kwargs):
        if self.client is None:
            raise RuntimeError("Client has not been added.")
        super(DriverInterface, self).request(method, **kwargs)

    def send(self) -> dict:
        """ Sends the stored requests to the driver.

        :return: The received response from the connected driver.
        """
        encoded = Transaction("client", input=self.requests).encoded()
        # if a decoding error occurs during communication, assume that it is because the
        # driver server has ended
        try:
            received = Transaction.decode("server", self.client.send(encoded))
        except ValueError:
            received = Transaction("server", error="ValueError: Unable to send package. Try again")
        # the requests are cleared to prevent the stacking of reactivated gates
        self.requests = []
        return received
