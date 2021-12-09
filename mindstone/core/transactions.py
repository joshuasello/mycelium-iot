# -*- coding: utf-8 -*-
""" Transaction Building Module.

NOTE: To encode and decode messages, msgpack is used instead of JSON, because of its
memory efficiency.
    https://github.com/msgpack/msgpack-python
"""

import msgpack


class _Structure(dict):
    """ Structure class.

    Defines the expected fields a transactions should contain.
    """

    def is_valid_entry(self, key: str, value) -> bool:
        if key not in self:
            return False
        if value is None:
            return True
        if "type" in self[key]:
            if not isinstance(value, self[key]["type"]):
                return False
        return True

    def is_valid_transaction(self, transaction: dict) -> bool:
        if self.keys() != transaction.keys():
            return False
        for key, value in transaction.items():
            if not self.is_valid_entry(key, value):
                return False
        return True


_structures = {
    "server": _Structure(
        received_time={
            "type": float
        },
        sent_time={
            "type": float
        },
        response={
            "type": dict
        },
        error={
            "type": str
        }
    ),
    "client": _Structure(
        input={
            "type": list
        }
    )
}


class Transaction(dict):
    """ Transaction class.

    Example:
        my_transaction = Transaction("server", received_time=time.time())
        ...
        return my_transaction.encoded()
        ...
        received_transaction = Transaction.decode("client", received)
    """

    def __init__(self, structure: str, **kwargs):
        # Populate this transaction with the provided values.
        # Left out fields are set to None
        super(Transaction, self).__init__(dict.fromkeys(_structures[structure]))
        self._structure_key = structure
        for key in kwargs.keys():
            self[key] = kwargs.get(key, None)

    def __setitem__(self, key, value):
        if not _structures[self._structure_key].is_valid_entry(key, value):
            raise ValueError("Tried to set a transaction item that does not adhere to the structure format.")
        super(Transaction, self).__setitem__(key, value)

    def encoded(self) -> bytes:
        # 1. check if this transaction is valid
        if not _structures[self._structure_key].is_valid_transaction(self):
            raise ValueError("Transaction to send does not match the structuring format '{}'".format(
                self._structure_key))
        # 2. encode the transaction for sending
        return msgpack.dumps(dict(**self))

    @staticmethod
    def decode(structure: str, received: bytes):
        return decode_transaction(structure, received)


def decode_transaction(structure: str, received: bytes) -> Transaction:
    # 1. decode the message
    decoded: dict = msgpack.loads(received)
    # 2. check the validity of the message
    if not _structures[structure].is_valid_transaction(decoded):
        raise RuntimeError("Received transaction does not match the structuring format '{}'".format(structure))
    return Transaction(structure, **decoded)
