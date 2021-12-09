# -*- coding: utf-8 -*-
""" mindstone python package.

The mindstone library provides a framework for designing and implementing
robots or agents control that is modularised, scalable and easy to implement.
Housing a collection of tools and models, the mindstone library can be used
to effectively create control models for anything from automating basic task
automation to controlling robots.

The goals of mindstone:
1. Provide a unified framework for building robot control models, both
    programmatically and graphically
2. Provide an extensive set of tools that can be used and embedded into
    control models.

TODO: Support access to devices on the system.
"""

__version__ = "1.0"

from mindstone.control.gatenetwork import *
from mindstone.control.tools import *
from mindstone.embedded import driver
