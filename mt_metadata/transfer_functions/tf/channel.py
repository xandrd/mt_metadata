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
from mt_metadata.base.helpers import write_lines
from mt_metadata.base import get_schema, Base
from .standards import SCHEMA_FN_PATHS

# =============================================================================
attr_dict = get_schema(name, SCHEMA_FN_PATHS)
# =============================================================================
class Channel(Base):
    __doc__ = write_lines(attr_dict)

    def __init__(self, **kwargs):
        self.type = "auxiliary"
        self.units = None
        self.channel_number = None
        self.channel_id = None
        self.comments = None
        self._component = None
        self.sample_rate = 0.0
        self.measurement_azimuth = 0.0
        self.measurement_tilt = 0.0
        self.data_quality = DataQuality()
        self.filter = Filtered()
        self.location = Location()
        self.time_period = TimePeriod()
        self.translated_azimuth = None
        self.translated_tilt = None
        self.sensor = Instrument()
        self.fdsn = Fdsn()

        super().__init__(attr_dict=attr_dict, **kwargs)

    @property
    def component(self):
        return self._component

    @component.setter
    def component(self, value):
        if value is not None:
            self._component = value.lower()


# =============================================================================
# auxiliary channel
# =============================================================================