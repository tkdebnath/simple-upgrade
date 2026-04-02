"""
Cisco manufacturer package.
"""

from . import sync
from . import readiness
from . import distribution
from . import activation
from . import checks
from . import verification

SUPPORTED_PLATFORMS = ['cisco_iosxe', 'cisco_xe', 'iosxe', 'cisco_ios']
