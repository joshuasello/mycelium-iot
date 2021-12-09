# -*- coding: utf-8 -*-
""" Platforms Subpackage.

"""

from mindstone.embedded.platforms import dummy
from mindstone.embedded.platforms.platform import current_platform, platform_is_set

supported_platforms = {
    "dummy": dummy.Platform
}

try:
    from mindstone.embedded.platforms import raspberrypi

    supported_platforms["rpi"] = raspberrypi.Platform
except ModuleNotFoundError:
    pass
