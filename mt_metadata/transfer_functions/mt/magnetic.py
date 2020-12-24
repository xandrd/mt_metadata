# -*- coding: utf-8 -*-
"""
Created on Wed Dec 23 21:30:36 2020

:copyright: 
    Jared Peacock (jpeacock@usgs.gov)

:license: MIT

"""
# =============================================================================
# Imports
# =============================================================================
from mt_metadata.helpers import write_lines
from mt_metadata.transfer_functions.mt.standards.schema import Standards

ATTR_DICT = Standards().ATTR_DICT
# =============================================================================
class Electric(Channel):
    __doc__ = write_lines(ATTR_DICT["electric"])

    def __init__(self, **kwargs):
        self.dipole_length = 0.0
        self.positive = Electrode()
        self.negative = Electrode()
        self.contact_resistance = Diagnostic()
        self.ac = Diagnostic()
        self.dc = Diagnostic()
        self.units_s = None

        Channel.__init__(self, **kwargs)
        self.type = "electric"

        self._attr_dict = ATTR_DICT["electric"]


# =============================================================================
# Magnetic Channel
# =============================================================================
