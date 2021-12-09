# -*- coding: utf-8 -*-
""" Gate Network Implementation.

A gate network interface implements a control system by connecting
what are called gates to each other to form a network of gates. When the
controller is activated, these connected gates can perform operations like
processing data or deciding where to send or redirect data to. Gates also
have the ability to act as a interface between controller and the driver
by sending and receiving data during the runtime of the controller.

More generally, a gate network controller is a directed graph where its nodes (the controller's gates)
are unit operations that perform specific tasks. An edge (or connection) between
two nodes represents the flow of data from one node to another. This makes it easy to
define, represent, and implement different types of control systems that may
suit different requirements.

This module contains:
- the gate network implementation
- the gate implementation, and
- pre-built handlers
"""

import json
import pickle
import warnings
from abc import ABC, abstractmethod
from collections.abc import Hashable, Iterable, Sized, Callable

import requests
from mindstone.control.graph import DirectedGraph, Node
from mindstone.control.interface import DriverInterface, RequestsWrapper
from mindstone.core.connection import client_types, server_types
from mindstone.core.utils import get_nested, update_item, TerminalColors

__all__ = ["GateNetwork", "Gate", "HTTPRequestHandler", "InjectionHandler", "RequestFactory"]

_standard_evaluators = {
    "eq": lambda a, b: a == b,
    "ne": lambda a, b: a != b,
    "lt": lambda a, b: a < b,
    "gt": lambda a, b: a > b,
    "le": lambda a, b: a <= b,
    "ge": lambda a, b: a >= b
}
"""dict: Holds functions that are used to compare two values.

The evaluator functions are used by the controller when handling conditional
gates. The first argument is the value corresponding to the conditional gate,
and the second is the value that is access from the input.
"""


class Gate(DriverInterface, Node, Callable):
    """ Gate Class.

    A gate represents a unit operation. They take some input,
    can do something based on that input, and can potentially return some output that could be used as the input
    for another gate.

    A gate will only perform its operation when activated by another gate. When one gate
    activates another, it passes on its output to the next gate so that it can be process.
    After the next gat has done its processing and has prepared its output, it can either
    activate another gate, continuing the process, or exit the controller and return its
    output.
    """

    def __init__(self, handler: Callable = None):
        super(Gate, self).__init__()
        self.context = None
        self._handler = handler

    def __str__(self) -> str:
        return "{}(handler={})".format(self.__class__.__name__, self._handler.__name__)

    def __call__(self, inserted: dict = None):
        return self.activate(inserted)

    def activate(self, inserted: dict = None):
        inserted = {} if inserted is None else inserted
        # 1. if a handler is set, apply it to the inserted data.
        handled = inserted if self._handler is None else self._handler(self, inserted)
        handled = {} if handled is None else handled
        # 2. A transaction between the controller and a driver can only occur when a gate
        # has an attached client object that define the communication channel for the
        # transaction. If none is set, return the direct result.
        if self.client is not None:
            # TODO: Review the decision to merge the response with the activation result.
            handled.update(self.send())
        return handled


class GateNetwork(DirectedGraph):
    """ Gate Network Class.

    Stores the collection of gates that implement the a system's control model
    and executes the control flow.

    """

    def __init__(self, clients: Iterable = None, gates: Sized = None, edges: Iterable = None):
        super(GateNetwork, self).__init__(nodes=gates, edges=edges)
        # dict: stores values that can be used by individual gates during the runtime
        # of the controller
        self.context = {}
        self.is_busy = False
        # dict: stores the addresses of specified client. The keys represent a label
        # given to a client.
        self._conditional_edges = {}
        # dict: stores all the conditional edges where a key is a edge tuple and a value
        # is a condition tuple of the form (key, evaluation, value)
        self._clients = {}
        # int: stores the number of times a generations of gates were processed.
        self.generation_count = 0
        # if given, define the initially provided hosts
        if clients is not None:
            for label, type, hostname, port in clients:
                self.define_client(label, type, hostname, port)

    def add_gate(self, key: Hashable, handler: Callable = None, client_label: str = None):
        """ Adds a new gate without having to directly use the gate object.

        :param key: The gate's unique key
        :param handler: The handler for the gate.
        :param client_label: Existing client to bind this gate to.
        :return: None
        """
        new_gate = Gate(handler)
        super(GateNetwork, self).add_node(key=key, node=new_gate)
        # prepare gate
        new_gate.context = self.context
        if client_label is not None:
            self.bind_to_client(key, client_label)

    def remove_gate(self, key: Hashable):
        super(GateNetwork, self).remove_node(key)

    def add_edge(self, from_gate: Hashable, to_gate: Hashable, key: Hashable = None,
                 value: Hashable = None, evaluator="eq", fallback: Hashable = None):
        """ Creates a connection from one gate to another.

        :param from_gate: Parent gate.
        :param to_gate: Child gate.
        :param key: Locates the value in the input data when the `to_gate` is activated
        :param value: Value that is compared against that key-value
        :param evaluator: Binary comparison function that returns a boolean value.
        :param fallback: The fallback gate key in the case that the condition evaluates to false
        :return: None
        """
        if key and evaluator and value is not None:
            evaluator = evaluator if callable(evaluator) else _standard_evaluators[evaluator]
            self._conditional_edges[(from_gate, to_gate)] = (key, evaluator, value)
            if fallback:
                # create the compliment conditional edge if a fallback is set
                self.add_edge(from_gate, fallback, key, value, lambda a, b: not evaluator(a, b))
        super(GateNetwork, self).add_edge(from_gate, to_gate)

    def remove_edge(self, from_gate: Hashable, to_gate: Hashable):
        """ Remove an edge from the network.

        :param from_gate: Parent gate.
        :param to_gate: Child gate.
        :return: None
        """
        edge = (from_gate, to_gate)
        if edge in self._conditional_edges:
            del self._conditional_edges[edge]
        super(GateNetwork, self).remove_edge(from_gate, to_gate)

    def define_client(self, label: str, target_hostname: str, target_port: int, type: str = "tcp"):
        """ Defines a new client.

        :param label: Unique label used to identify the client.
        :param target_hostname: Target hostname.
        :param target_port: Target port.
        :param type: Type of connection used by the client.
        :return: None.
        """
        if self.client_exists(type, target_hostname, target_port):
            raise RuntimeError("Tried to define a client '{}' that already exists. A client must "
                               "have a unique label and a unique info (type, hostname, and port).".format(label))
        self._clients[label] = client_types[type](target_hostname, target_port)

    def delete_client(self, label: str):
        """ Delete an added client and its references from added gates.

        :param label: Client label.
        :return: None.
        """
        type, target_hostname, target_port = self._clients.pop(label)
        for gate in self.values():
            if isinstance(gate.client, client_types[type]):
                if gate.client.target_address == (target_hostname, target_port):
                    gate.client = None

    def client_exists(self, type: str, target_hostname: str, target_port: int) -> bool:
        """ Checks if a client with matching details already exists.

        NOTE: A client is aloud to have the same address if they use different connection types.

        :param type: Type of connection used by the client.
        :param target_hostname: Target hostname.
        :param target_port: Target port.
        :return: True if the client exists otherwise false.
        """
        for client in self._clients.values():
            if client.target_address == (target_hostname, target_port) and isinstance(client, client_types[type]):
                return True
        return False

    def bind_to_client(self, gate_key: Hashable, client_label: str):
        """ Assign a gate in the controller to a specified client.

        :param gate_key: key of the gate to bind
        :param client_label: the label of the host.
        :return: None
        """
        self[gate_key].client = self._clients[client_label]

    def run(self, start: Hashable, initial_payload=None):
        """ Run the controller.

        :param start: The first gate to be activated
        :param initial_payload: Data that is passed into the first activated gate.
        :return: The output of the last activated gate.
        """
        self.is_busy = True
        # 1. check if anny gates have no other gates connected to it
        # and warn the user if there are more than one gates.
        isolated = self.isolated()
        if len(isolated) and len(self):
            warnings.warn("Isolated: {}".format(', '.join(isolated)))
        # 2. finally, run the network and return the result
        result = self._resolve(start, initial_payload)
        self.is_busy = False
        return result

    def listen(self, hostname: str, port: int, connection_type: str = "tcp"):
        # start connection server
        print("{}STARTING GATE NETWORK SERVER @ ({}, {}){}".format(
            TerminalColors.HEADER, hostname, port, TerminalColors.ENDC))
        print("Press CTRL+C to end the server.")
        print("-" * 50)
        server_types[connection_type].serve(hostname=hostname, port=port, on_receive=self._on_receive)

    def to_pickle(self) -> bytes:
        """ Gets the pickle serialization of this controller.

        :return: The pickle serialization.
        """
        return pickle.dumps(self)

    def _on_receive(self, received: bytes, client_address: tuple = None) -> bytes:
        if not self.is_busy:
            print("Received Request from {}".format(client_address))
            request_data = json.loads(received.decode("utf-8"))
            return json.dumps(self.run(
                start=request_data["start"],
                initial_payload=request_data["payload"] if "payload" in request_data else None
            )).encode("utf-8")
        else:
            return b"BUSY"

    def _get_next_generation(self, current: dict, carry_overs: dict, completed: dict) -> tuple:
        next_generation = {}
        next_gates = {}
        for gate_key, activation_result in current.items():
            activation_result = {} if activation_result is None else activation_result
            # if a gate has no children then nothing should happen to it.
            # append it to the complete list and move on
            if not len(self[gate_key]):
                completed[gate_key] = activation_result
                continue
            # 1. get current gates
            for child in self[gate_key]:
                edge = (gate_key, child)
                next_gate_key = child
                is_conditional = edge in self._conditional_edges
                # conditional evaluation
                if is_conditional:
                    key, evaluator, value = self._conditional_edges[edge]
                    if evaluator(value, get_nested(key, activation_result)):
                        next_gate_key = child
                    else:
                        continue
                # evaluate if this gate should be activated in this generation
                # A clause in how the parents are selected allows for gate one gate gate to call
                # to another gate and that gate to call back to that gate. This is done on purpose.
                parents = {
                    parent for parent in self.in_neighbors(next_gate_key)
                    if not (is_conditional or (parent, child) in self._conditional_edges or parent != gate_key)
                }
                carry_over_parents = set()
                next_gate_payload = activation_result
                if next_gate_key in carry_overs:
                    for parent_key, parent_activation_result in carry_overs.pop(next_gate_key).items():
                        carry_over_parents.add(parent_key)
                        next_gate_payload.update(parent_activation_result)
                if parents.issubset(carry_over_parents.union(current)):
                    # gates with multiple parents in the same
                    update_item(next_gates, next_gate_key, next_gate_payload)
                else:
                    update_item(carry_overs, next_gate_key, {gate_key: activation_result})
        for next_gate_key, activation_input in next_gates.items():
            next_generation[next_gate_key] = self[next_gate_key](activation_input)
        return next_generation, carry_overs

    def _resolve(self, gate_key: Hashable, payload: dict) -> dict:
        # In a previous implementation, I used recursion to activate each gate that needed to be activated.
        # This limited the amount of iterations a gate could call itself due to recursion errors. Instead,
        # I have opted to use a while loop. This means that a gate can call on its indefinitely.
        current_generation = {
            gate_key: self[gate_key](payload)
        }
        carry_overs = {}
        completed = {}
        while True:
            self.generation_count += 1
            current_generation, carry_overs = self._get_next_generation(current_generation, carry_overs, completed)
            if not len(current_generation):
                return completed


class _HandlerABC(ABC, Callable):
    """ Handler Abstract Base Class.

    """

    def __init__(self):
        self.__name__ = self.__class__.__name__

    @abstractmethod
    def __call__(self, gate: Gate, payload: dict):
        pass


class HTTPRequestHandler(_HandlerABC):
    """ HTTP Request Handler Class.

    """

    _http_method_handlers = {
        "GET": lambda url, data: requests.get(url=url, params=data),
        "POST": lambda url, data: requests.post(url=url, data=data)
    }

    _response_formatters = {
        "json": lambda response: response.json()
    }

    def __init__(self, url: str, request_method: str = "GET", response_format: str = "json"):
        super(HTTPRequestHandler, self).__init__()
        self._url = url
        self._method = request_method.upper().strip()
        self._format = response_format.lower().strip()

    def __call__(self, gate: Gate, payload: dict = None):
        return self._response_formatters[self._format](self._http_method_handlers[self._method](
            self._url, {} if payload is None else payload))


class InjectionHandler(dict, _HandlerABC):
    """ Injection Handler Class.

    """

    def __call__(self, gate: Gate, payload: dict):
        payload = {} if payload is None else payload
        payload.update(self)
        return payload


class RequestFactory(RequestsWrapper, _HandlerABC):
    """ Request Factory Class.

    """

    def __call__(self, gate, payload: dict):
        gate.requests = self.requests
        return payload
