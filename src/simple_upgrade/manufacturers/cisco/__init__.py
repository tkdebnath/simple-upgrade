"""
Cisco manufacturer package.
"""

from . import sync
from . import readiness
from . import distribution
from . import activation
from . import checks
from . import verification
from . import diff

SUPPORTED_PLATFORMS = ['cisco_iosxe', 'cisco_xe', 'iosxe', 'cisco_ios']
