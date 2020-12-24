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
class Station(Base):
    __doc__ = write_lines(ATTR_DICT["station"])

    def __init__(self, **kwargs):
        self.id = None
        self.fdsn = Fdsn()
        self.geographic_name = None
        self.datum = None
        self.num_channels = None
        self.channels_recorded = []
        self.run_list = []
        self.channel_layout = None
        self.comments = None
        self.data_type = None
        self.orientation = Orientation()
        self.acquired_by = Person()
        self.provenance = Provenance()
        self.location = Location()
        self.time_period = TimePeriod()
        self.transfer_function = TransferFunction()

        super().__init__(attr_dict=ATTR_DICT["station"], **kwargs)

    @property
    def run_names(self):
        runs = []
        for rr in self.run_list:
            if isinstance(rr, Run):
                runs.append(rr.id)
            else:
                runs.append(rr)
        return runs


# =============================================================================
# Run
# =============================================================================
