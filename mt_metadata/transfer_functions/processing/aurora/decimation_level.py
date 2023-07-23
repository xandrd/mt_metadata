# -*- coding: utf-8 -*-
"""
Created on Thu Feb 17 14:15:20 2022

@author: jpeacock
"""
# =============================================================================
# Imports
# =============================================================================
import numpy as np

from mt_metadata.base.helpers import write_lines
from mt_metadata.base import get_schema, Base
from mt_metadata.transfer_functions.processing.aurora.frequency_band import (
    get_fft_harmonics,
)
from mt_metadata.transfer_functions.processing.aurora import (
    Decimation as FourierCoefficientDecimation,
)

from .standards import SCHEMA_FN_PATHS

from .window import Window
from .decimation import Decimation
from .band import Band
from .regression import Regression
from .estimator import Estimator

# =============================================================================
attr_dict = get_schema("decimation_level", SCHEMA_FN_PATHS)
attr_dict.add_dict(get_schema("decimation", SCHEMA_FN_PATHS), "decimation")
attr_dict.add_dict(get_schema("window", SCHEMA_FN_PATHS), "window")
attr_dict.add_dict(get_schema("regression", SCHEMA_FN_PATHS), "regression")
attr_dict.add_dict(get_schema("estimator", SCHEMA_FN_PATHS), "estimator")


# =============================================================================
class DecimationLevel(Base):
    __doc__ = write_lines(attr_dict)

    def __init__(self, **kwargs):

        self.window = Window()
        self.decimation = Decimation()
        self.regression = Regression()
        self.estimator = Estimator()

        self._bands = []

        super().__init__(attr_dict=attr_dict, **kwargs)

    @property
    def bands(self):
        """
        get bands, something weird is going on with appending.

        """
        return_list = []
        for band in self._bands:
            if isinstance(band, dict):
                b = Band()
                b.from_dict(band)
            elif isinstance(band, Band):
                b = band
            return_list.append(b)
        return return_list

    @bands.setter
    def bands(self, value):
        """
        Set bands make sure they are a band object

        :param value: list of bands
        :type value: list, Band

        """

        if isinstance(value, Band):
            self._bands = [value]

        elif isinstance(value, list):
            self._bands = []
            for obj in value:
                if not isinstance(obj, (Band, dict)):
                    raise TypeError(
                        f"List entry must be a Band object not {type(obj)}"
                    )
                if isinstance(obj, dict):
                    band = Band()
                    band.from_dict(obj)

                else:
                    band = obj

                self._bands.append(band)
        else:
            raise TypeError(f"Not sure what to do with {type(value)}")

    def add_band(self, band):
        """
        add a band
        """

        if not isinstance(band, (Band, dict)):
            raise TypeError(
                f"List entry must be a Band object not {type(band)}"
            )
        if isinstance(band, dict):
            obj = Band()
            obj.from_dict(band)

        else:
            obj = band

        self._bands.append(obj)

    @property
    def lower_bounds(self):
        """
        get lower bounds index values into an array.
        """

        return np.array(sorted([band.index_min for band in self.bands]))

    @property
    def upper_bounds(self):
        """
        get upper bounds index values into an array.
        """

        return np.array(sorted([band.index_max for band in self.bands]))

    @property
    def bands_dataframe(self):
        """
        This is just a utility function that transforms a list of bands into a dataframe
        ToDo: Consider make this a method of Bands()

        Note: The decimation_level here is +1 to agree with EMTF convention.
        Not clear this is really necessary

        ToDo: Consider adding columns lower_edge, upper_edge to df

        Returns
        -------
        bands_df: pd.Dataframe
            Same format as that generated by EMTFBandSetupFile.get_decimation_level()
        """
        from mt_metadata.transfer_functions.processing.aurora.frequency_band import (
            df_from_bands,
        )

        bands_df = df_from_bands(self.bands)
        return bands_df

    @property
    def band_edges(self):
        bands_df = self.bands_dataframe
        band_edges = np.vstack(
            (bands_df.frequency_min.values, bands_df.frequency_max.values)
        ).T
        return band_edges

    def frequency_bands_obj(self):
        """
        Gets a FrequencyBands object that is used as input to processing.
        This used to be needed because I only had

        ToDO: consider adding .to_frequnecy_bands() method directly to self.bands
        Returns
        -------

        """
        from mt_metadata.transfer_functions.processing.aurora.frequency_band import (
            FrequencyBands,
        )

        frequency_bands = FrequencyBands(band_edges=self.band_edges)
        return frequency_bands

    @property
    def fft_frequecies(self):
        freqs = get_fft_harmonics(
            self.window.num_samples, self.decimation.sample_rate
        )
        return freqs

    @property
    def sample_rate_decimation(self):
        return self.decimation.sample_rate

    def harmonic_indices(self):
        harmonic_indices = []
        for band in self.bands:
            fc_indices = np.arange(band.index_min, band.index_max + 1)
            harmonic_indices += fc_indices.tolist()
        harmonic_indices.sort()
        return harmonic_indices

    def to_fc_decimation(self, local_or_remote):
        """
        Generates a Decimation() object for use with FC Layer in mth5.
        Note that the property is assigned harmonic_indices_required, which is not in the formal schema of the output
        Decimation() object.  This is there to capture the FC indices that are required to process the TF, to allow
        checking for these in the FC Level, in order to validate that the archived FC Level contains the needed data
        for processing.

        ToDo: Consider making local_or_remote a kwarg, with default value None.  While it may be useful at times to only
        generate FCs for selected channels, in general we will normally wish to estimate all channels for archiving
        purposes.
        Args:
            local_or_remote: str
            ["local", "remote", "RR"]

        Returns:
            fc_dec_obj:mt_metadata.transfer_functions.processing.fourier_coefficients.decimation.Decimation
            A decimation object configured for STFT processing

        """

        fc_dec_obj = FourierCoefficientDecimation()
        fc_dec_obj.anti_alias_filter = self.anti_alias_filter
        if local_or_remote.lower() == "local":
            fc_dec_obj.channels_estimated = (
                self.input_channels + self.output_channels
            )
        elif local_or_remote.lower() in [
            "remote",
            "rr",
        ]:
            fc_dec_obj.channels_estimated = self.reference_channels
        fc_dec_obj.decimation_factor = self.decimation.factor
        fc_dec_obj.decimation_level = self.decimation.level
        fc_dec_obj.harmonic_indices_required = self.harmonic_indices()
        fc_dec_obj.id = "undefined when sourced from decimation_level.py"
        fc_dec_obj.method = "fft"
        fc_dec_obj.pre_fft_detrend_type = self.pre_fft_detrend_type
        fc_dec_obj.prewhitening_type = self.prewhitening_type
        fc_dec_obj.recoloring = self.recoloring
        fc_dec_obj.sample_rate_decimation = self.sample_rate_decimation
        fc_dec_obj.window = self.window

        return fc_dec_obj
