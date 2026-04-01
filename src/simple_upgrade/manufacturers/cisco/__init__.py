"""
Cisco manufacturer-specific upgrade implementations.

Supports:
    - Cisco IOS-XE (Catalyst 9K, 3650, etc.)
    - Cisco NX-OS (Nexus 9K, etc.)
"""

from . import sync, readiness, distribution, activation, verification

__all__ = ['sync', 'readiness', 'distribution', 'activation', 'verification']
