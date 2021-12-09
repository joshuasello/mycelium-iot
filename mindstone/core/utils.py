# -*- coding: utf-8 -*-
""" Utils sub-package.

"""

import inspect
import time
from collections.abc import Callable


class TerminalColors:
    """
        Terminal Colors class.

        Source:
            - https://svn.blender.org/svnroot/bf-blender/trunk/blender/build_files/scons/tools/bcolors.py

        Example:
            print(bcolors.WARNING + "Warning: No active frommets remain. Continue?" + bcolors.ENDC)
            print(f"{bcolors.WARNING}Warning: No active frommets remain. Continue?{bcolors.ENDC}")

    """
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

    def disable(self):
        self.HEADER = ''
        self.OKBLUE = ''
        self.OKGREEN = ''
        self.WARNING = ''
        self.FAIL = ''
        self.ENDC = ''


def get_args(func: Callable) -> set:
    """ Get the arguments for a function.

    :param func: Function under inspection.
    :return: Set of arguments.
    """
    return set(inspect.getfullargspec(func)[0])


def get_required_args(func: Callable) -> set:
    """ Get the required (non-default) arguments for a function.

    source: https://stackoverflow.com/questions/196960/can-you-list-the-keyword-arguments-a-function-receives

    :param func: Function under inspection.
    :return: Set of required arguments.
    """
    args, varargs, varkw, defaults, kwonlyargs, kwonlydefaults, annotations = inspect.getfullargspec(func)
    return set(args[:-len(defaults)] if defaults else args)  # *args and **kwargs are not required, so ignore them.


def time_function(function):
    def timed(*args, **kwargs):
        ts = time.perf_counter()
        result = function(*args, **kwargs)
        te = time.perf_counter()
        if 'log_time' in kwargs:
            name = kwargs.get('log_name', function.__name__.upper())
            kwargs['log_time'][name] = int((te - ts) * 1000)
        else:
            print('%r  %2.2f ms' % (function.__name__, (te - ts) * 1000))
        return result

    return timed


def update_item(mapping: dict, key, value) -> dict:
    """ Update a item that is also a dictionary

    :param mapping: The container dictionary.
    :param key: Key of the updatable item.
    :param value: The value to update the item with.
    :return: None
    """
    if key in mapping:
        mapping[key].update(value)
    else:
        mapping[key] = value
    return mapping


def get_nested(route: str, mapping: dict, delimiter: str = "."):
    return _get_nested_util(route.split(delimiter), mapping)


def _get_nested_util(route: list, mapping):
    key = route.pop(0)
    if key not in mapping:
        return None
    mapping = mapping[key]
    return mapping if not len(route) else _get_nested_util(route, mapping)
