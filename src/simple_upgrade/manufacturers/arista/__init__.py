"""
Arista manufacturer-specific upgrade implementations.

Supports:
    - Arista EOS (7050, 7100, 7250, 7500 series)
"""

from . import sync, readiness, distribution, activation, verification

__all__ = ['sync', 'readiness', 'distribution', 'activation', 'verification']
