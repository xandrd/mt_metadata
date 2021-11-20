"""
Channel Response Filter
=========================

Combines all filters for a given channel into a total response that can be used in 
the frequency domain.

.. note:: Time Delay filters should be applied in the time domain otherwise bad
things can happen.   

"""
# =============================================================================
# Imports
# =============================================================================
import numpy as np

from mt_metadata.timeseries.filters import (
    PoleZeroFilter,
    CoefficientFilter,
    TimeDelayFilter,
    FrequencyResponseTableFilter,
    FIRFilter,
)
from mt_metadata.utils.units import get_unit_object
from mt_metadata.utils.mt_logger import setup_logger
from mt_metadata.timeseries.filters.plotting_helpers import plot_response
from obspy.core import inventory

# =============================================================================


class ChannelResponseFilter(object):
    """
    This class holds a list of all the filters associated with a channel.
    It has methods for combining the responses of all the filters into a total
    response that we will apply to a data segment.

    """

    def __init__(self, **kwargs):
        self.filters_list = []
        self.frequencies = np.logspace(-4, 4, 100)
        self.normalization_frequency = None
        self.logger = setup_logger(f"{self.__class__}.{self.__class__.__name__}")

        for k, v in kwargs.items():
            setattr(self, k, v)

    def __str__(self):
        lines = ["Filters Included:\n", "=" * 25, "\n"]
        for f in self.filters_list:
            lines.append(f.__str__())
            lines.append(f"\n{'-'*20}\n")

        return "".join(lines)

    def __repr__(self):
        return self.__str__()

    @property
    def filters_list(self):
        """filters list"""
        return self._filters_list

    @filters_list.setter
    def filters_list(self, filters_list):
        """set the filters list and validate the list"""
        self._filters_list = self._validate_filters_list(filters_list)
        
    @property
    def frequencies(self):
        """ frequencies to estimate filters """
        return self._frequencies
    
    @frequencies.setter
    def frequencies(self, value):
        """
        Set the frequencies, make sure the input is validated

        Linear frequencies
        :param value: Linear Frequencies
        :type value: iterable

        """
        if value is None:
            self._frequencies = None
            
        elif isinstance(value, (list, tuple, np.ndarray)):
            self._frequencies = np.array(value, dtype=float)
        else:
            msg = (
                f"input values must be an list, tuple, or np.ndarray, not {type(value)}"
            )
            self.logger.error(msg)
            raise TypeError(msg)

    @property
    def names(self):
        """names of the filters"""
        names = []
        if self.filters_list:
            names = [f.name for f in self.filters_list]
        return names

    def _validate_filters_list(self, filters_list):
        """
        make sure the filters list is valid

        :param filters_list: DESCRIPTION
        :type filters_list: TYPE
        :return: DESCRIPTION
        :rtype: TYPE

        """
        ACCEPTABLE_FILTERS = [
            PoleZeroFilter,
            CoefficientFilter,
            TimeDelayFilter,
            FrequencyResponseTableFilter,
            FIRFilter,
        ]

        def is_acceptable_filter(item):
            if isinstance(item, tuple(ACCEPTABLE_FILTERS)):
                return True
            else:
                return False

        if filters_list in [[], None]:
            return []

        if not isinstance(filters_list, list):
            msg = "Input filters list must be a list not %s"
            self.logger.error(msg, type(filters_list))
            raise TypeError(msg % type(filters_list))

        fails = []
        return_list = []
        for item in filters_list:
            if is_acceptable_filter(item):
                return_list.append(item)
            else:
                fails.append(f"Item is not an acceptable filter type, {type(item)}")

        if fails:
            raise TypeError(", ".join(fails))

        return return_list

    @property
    def pass_band(self):
        """estimate pass band for all filters in frequency"""
        if self.frequencies is None:
            raise ValueError(
                "frequencies are None, must be input to calculate pass band")
        pb = []
        for f in self.filters_list:
            if hasattr(f, "pass_band"):
                f_pb = f.pass_band(self.frequencies)
                if f_pb is None:
                    continue
                pb.append((f_pb.min(), f_pb.max()))

        if pb is not []:
            pb = np.array(pb)
            return np.array([pb[:, 0].max(), pb[:, 1].min()])
        return None

    @property
    def normalization_frequency(self):
        """get normalization frequency from ZPK or FAP filter"""

        if self._normalization_frequency is None:
            if self.pass_band is not None:
                return np.round(self.pass_band.mean(), decimals=3)
            return None

        return self._normalization_frequency

    @normalization_frequency.setter
    def normalization_frequency(self, value):
        """Set normalization frequency if input"""

        self._normalization_frequency = value

    @property
    def non_delay_filters(self):
        """

        Returns all the non-time_delay filters as a list
        -------

        """
        non_delay_filters = [x for x in self.filters_list if x.type != "time delay"]
        return non_delay_filters

    @property
    def delay_filters(self):
        """

        Returns all the time delay filters as a list
        -------

        """
        delay_filters = [x for x in self.filters_list if x.type == "time delay"]
        return delay_filters

    @property
    def total_delay(self):
        """

        Returns the total delay of all filters
        -------

        """
        delay_filters = self.delay_filters
        total_delay = 0.0
        for delay_filter in delay_filters:
            total_delay += delay_filter.delay
        return total_delay

    def complex_response(
        self, 
        frequencies=None, 
        include_delay=False,
        normalize=False,
        include_decimation=True,
        **kwargs,
    ):
        """

        Parameters
        ----------
        frequencies: numpy array of frequencies, expected in Hz

        Returns
        -------
        h : numpy array of (possibly complex-valued) frequency response at the input frequencies

        """
        if frequencies is not None:
            self.frequencies = frequencies

        if include_delay:
            filters_list = self.filters_list
        else:
            filters_list = self.non_delay_filters

        if not include_decimation:
            filters_list = [x for x in filters_list if not x.decimation_active]

        if len(filters_list) == 0:
            # warn that there are no filters associated with channel?
            return np.ones(len(frequencies))

        filter_stage = filters_list.pop(0)
        result = filter_stage.complex_response(frequencies, **kwargs)
        while len(filters_list):
            filter_stage = filters_list.pop(0)
            result *= filter_stage.complex_response(frequencies, **kwargs)

        if normalize:
            result /= np.max(np.abs(result))
        return result

    def compute_instrument_sensitivity(self, normalization_frequency=None):
        """
        Compute the StationXML instrument sensitivity for the given normalization frequency

        :param normalization_frequency: DESCRIPTION
        :type normalization_frequency: TYPE
        :return: DESCRIPTION
        :rtype: TYPE

        """
        if normalization_frequency is not None:
            self.normalization_frequency = normalization_frequency
        sensitivity = 1.0
        for mt_filter in self.filters_list:
            complex_response = mt_filter.complex_response(self.normalization_frequency)
            sensitivity *= complex_response.astype(complex)
        try:
            return np.round(np.abs(sensitivity[0]), 3)
        except (IndexError, TypeError):
            return np.round(np.abs(sensitivity), 3)

    @property
    def units_in(self):
        """
        returns the units of the channel
        """
        return self.filters_list[0].units_in

    @property
    def units_out(self):
        """
        returns the units of the channel
        """
        return self.filters_list[-1].units_out

    @property
    def check_consistency_of_units(self):
        """
        confirms that the input and output units of each filter state are consistent
        """
        previous_units = self.filters_list[0].units_out
        for mt_filter in self.filters_list[1:]:
            if mt_filter.units_in != previous_units:
                msg = (
                    f"Unit consistency is incorrect,  {previous_units} != {mt_filter.units_in}"
                    f" For filter {mt_filter.name}"
                )
                raise ValueError(msg)
            previous_units = mt_filter.units_out

        return True

    def to_obspy(self, sample_rate=1):
        """
        Output :class:`obspy.core.inventory.InstrumentSensitivity` object that
        can be used in a stationxml file.

        :param normalization_frequency: DESCRIPTION
        :type normalization_frequency: TYPE
        :return: DESCRIPTION
        :rtype: TYPE

        """
        total_sensitivity = self.compute_instrument_sensitivity()

        units_in_obj = get_unit_object(self.units_in)
        units_out_obj = get_unit_object(self.units_out)

        total_response = inventory.Response()
        total_response.instrument_sensitivity = inventory.InstrumentSensitivity(
            total_sensitivity,
            self.normalization_frequency,
            units_in_obj.abbreviation,
            units_out_obj.abbreviation,
            input_units_description=units_in_obj.name,
            output_units_description=units_out_obj.name,
        )

        for ii, f in enumerate(self.filters_list, 1):
            if f.type in ["coefficient"]:
                if f.units_out not in ["count"]:
                    self.logger.debug("converting CoefficientFilter %s to PZ", f.name)
                    pz = PoleZeroFilter()
                    pz.gain = f.gain
                    pz.units_in = f.units_in
                    pz.units_out = f.units_out
                    pz.comments = f.comments
                    pz.name = f.name
                else:
                    pz = f

                total_response.response_stages.append(
                    pz.to_obspy(
                        stage_number=ii,
                        normalization_frequency=self.normalization_frequency,
                        sample_rate=sample_rate,
                    )
                )
            else:
                total_response.response_stages.append(
                    f.to_obspy(
                        stage_number=ii,
                        normalization_frequency=self.normalization_frequency,
                        sample_rate=sample_rate,
                    )
                )

        return total_response
    
    def plot_response(self, frequencies=None, x_units="period", unwrap=True,
                      pb_tol=1e-1, interpolation_method="slinear"):
            
        if frequencies is not None:
            self.frequencies = frequencies
        
        cr_kwargs = {"interpolation_method": interpolation_method}

        complex_response = self.complex_response(self.frequencies, **cr_kwargs)
            
        cr_list = [f.complex_response(self.frequencies, **cr_kwargs) for f in self.filters_list]
        cr_list.append(complex_response)
        labels = [f.name for f in self.filters_list] + ["Total Response"]
       
        kwargs = {
            "title": f"Channel Response: [{', '.join([f.name for f in self.filters_list])}]",
            "unwrap": unwrap,
            "x_units": x_units,
            "pass_band": self.pass_band,
            "label": labels}
        
        plot_response(self.frequencies, cr_list, **kwargs)
