"""Class for PSF data."""

import warnings
from typing import Optional

from metroloshiny.utils.common_utils import get_today


class PSFData:
    """
    Class that represents PSF data retrieved from OMERO.

    Currently only for PSF_Inspector.py generated data.
    """

    def __init__(self, data: dict):
        self.data = data
        self.n_channels = None
        self.channel_names = []  # ch-names read from key-value pairs (e.g. C2)
        self.acquisition_date = None
        self.na = None
        self.objective = None  # Magnification
        # Individual data: keys = channels; values = dict
        self.individual_data = {}
        # In case there is already averaged data
        self.average_data = {}
        # Shifts to reference (averaged vals): keys = channels; values = dict
        self.shift_data = {}
        # The FINAL FWHM data dict[dict]
        self.fwhm_data = {}

        # Parse the input data
        self._set_channel_names_()
        self._get_metadata_()
        self._parse_data_()
        self._set_final_fwhm_data_()

    # Getters / Setters     --------------------------------------------------

    def get_fwhm_data(self) -> dict[str, dict[str, float]]:
        """Getter for the FWHM data."""
        return self.fwhm_data

    def get_shift_data(self) -> dict[str, dict[str, float]]:
        """Getter for shift data."""
        return self.shift_data

    def get_acquisition_date(self) -> Optional[str]:
        """Getter for the acquisition date."""
        return self.acquisition_date

    def inject_channel_names(self, ch_names: list):
        """Overwrite channel names with supplied ones."""
        # Do not adjust channel names if len(injected list) != n_channels
        if len(ch_names) != self.n_channels:
            return
        # Do not adjust channel names if there are duplicates in the list
        if len(ch_names) != len(set(ch_names)):
            return
        # Otherwise adjust the names in the final data dictionaries
        new_fwhm = {}
        new_shift = {}
        for i in range(len(self.channel_names)):
            old_name = self.channel_names[i]
            new_name = ch_names[i]
            # Rename the channel keys in the final data dictionaries
            new_fwhm[new_name] = self.fwhm_data.get(old_name)
            # Same for shift data, only if there is any
            if self.shift_data:
                new_shift[new_name] = self.shift_data.get(old_name)
        # Overwrite the existing dictionaries
        self.fwhm_data = new_fwhm
        if self.shift_data:
            self.shift_data = new_shift
        # Also set the channel names list
        self.channel_names = ch_names

    def inject_voxel_size(self, voxels: list[float]):
        """Calibrate shift data with voxel size."""
        # Do not modify if there is not XYZ voxel sizes
        if len(voxels) != 3:
            return
        # Do not modify if there is not data to modify
        if not self.shift_data:
            return
        # Modify the voxel sizes
        new_shifts = {}
        for ch, shifts in self.shift_data.items():
            for shift, value in shifts.items():
                new_value = value
                voxel_index = None
                if "X" in shift:
                    voxel_index = 0
                elif "Y" in shift:
                    voxel_index = 1
                elif "Z" in shift:
                    voxel_index = 2
                else:
                    raise RuntimeError(
                        f"Could not calibrate shift-value = {ch}:{shift}"
                    )
                # Try calibrating (skip for non floats, e.g. References)
                try:
                    new_value = round(float(value) * voxels[voxel_index], 6)
                except ValueError:
                    pass
                # Add the value to the new dictionary
                if ch not in new_shifts.keys():
                    new_shifts[ch] = {
                        "Shift-X": None,
                        "Shift-Y": None,
                        "Shift-Z": None,
                    }
                # Add shift-x values
                if voxel_index == 0:
                    new_shifts[ch]["Shift-X"] = new_value
                if voxel_index == 1:
                    new_shifts[ch]["Shift-Y"] = new_value
                if voxel_index == 2:
                    new_shifts[ch]["Shift-Z"] = new_value
        # Finally, replace the shift data
        self.shift_data = new_shifts

    # Functions      ---------------------------------------------------------

    def _set_channel_names_(self):
        """Set the channel names according to the key-value pairs."""
        for k in self.data.keys():
            if "FWHM_Axial" in k:
                # Get the ch-name
                ch = k.split("_")[0]
                # Add the name to the list
                if ch not in self.channel_names:
                    self.channel_names.append(ch)
        # Sanity check (should not happen)
        if len(self.channel_names) == self.n_channels:
            raise RuntimeError(
                "Number of channel names is not equal to channels"
            )

    def _set_final_fwhm_data_(
        self, min_fwhm: int = 150, compare: bool = False
    ):
        """
        Check if average the average is correct.

        Sets the final fwhm_data dictionary.
        This function will never allow the OMERO averaged FWHM values
        to be the final ones, it will always calculate them from scratch.

        I.e. average the of the individual bead FWHM values matches
        the OMERO calculated values.
        It removes "wrong" values, if they are below 150 (nm).

        :param min_fwhm: int minimal fwhm value to beconiderd as "not wrong"
        :param compare: bool, will compare to OMERO average data and
            raise RuntimeWarnings if values are not the same.
        """
        # Check if there is multiple values to average
        v = self.individual_data[next(iter(self.individual_data))].get(
            "FWHM-X"
        )
        if len(v) == 1:
            # Convert the list of FWHM values to single value
            # and set the final fwhm data dict
            for ch in self.individual_data.keys():
                channel_dict = {}
                for k, v in self.individual_data[ch].items():
                    # Does not check for "wrong" values
                    channel_dict[k] = float(v[0])
                self.fwhm_data[ch] = channel_dict
            return

        # Average the individual data
        avg_individual = {}
        for ch in self.individual_data.keys():
            channel_dict = {}
            for k, v in self.individual_data[ch].items():
                # Average the values if bigger than min_fwhm
                avg = self._average_values_(v, min_fwhm=min_fwhm)
                channel_dict[k] = avg
            avg_individual[ch] = channel_dict
        # Set the calculated averages as the final fwhm
        self.fwhm_data = avg_individual

        # If there is no averaged data
        if len(self.average_data) == 0:
            return

        # Check if the calculated averages match the OMERO ones
        if compare:
            for ch, ch_vals in avg_individual.items():
                for k, v in ch_vals.items():
                    avg_omero = self.average_data[ch].get(k)
                    if round(v) != round(avg_omero):
                        warnings.warn(
                            f"Calculated {k} deviates from OMERO average: "
                            f"{v} vs {avg_omero}.",
                            stacklevel=2,
                        )

    def _average_values_(self, values: list, min_fwhm: int):
        """
        Average a list of values if value > min_fwhm.

        Returns 0.0 if all values are below min_fwhm.

        :param values: list of values
        :param min_fwhm: int min value

        :return: float of rounded int
        """
        count = 0
        sum = 0
        for v in values:
            try:
                val = int(v)
            except ValueError as err:
                raise RuntimeError(
                    f"Could not parse FHMW value <{v}> to a number."
                ) from err
            if val > min_fwhm:
                count = count + 1
                sum = sum + val
        if count == 0:
            return 0.0
        return float(round(float(sum) / count, 1))

    def _parse_data_(self):
        """Parse the data from OMERO."""
        for k, v in self.data.items():
            # Check for already averaged PSF values   ------------------------
            if "AVERAGE_FWHM_X" in k:
                ch = k.split("_")[-1]
                if ch in self.average_data.keys():
                    d = self.average_data[ch]
                    if "FWHM-X" in d.keys():
                        raise RuntimeError(
                            "Found multiple average PSF values "
                            f"for channel {ch} FWHM-X."
                        )
                    else:
                        self.average_data[ch]["FWHM-X"] = v
                else:
                    self.average_data[ch] = {"FWHM-X": v}
            if "AVERAGE_FWHM_Y" in k:
                ch = k.split("_")[-1]
                if ch in self.average_data.keys():
                    d = self.average_data[ch]
                    if "FWHM-Y" in d.keys():
                        raise RuntimeError(
                            "Found multiple average PSF values "
                            f"for channel {ch} FWHM-Y."
                        )
                    else:
                        self.average_data[ch]["FWHM-Y"] = v
                else:
                    self.average_data[ch] = {"FWHM-Y": v}
            if "AVERAGE_FWHM_Z" in k:
                ch = k.split("_")[-1]
                if ch in self.average_data.keys():
                    d = self.average_data[ch]
                    if "FWHM-Z" in d.keys():
                        raise RuntimeError(
                            "Found multiple average PSF values "
                            f"for channel {ch} FWHM-Z."
                        )
                    else:
                        self.average_data[ch]["FWHM-Z"] = v
                else:
                    self.average_data[ch] = {"FWHM-Z": v}

            # Check for individual PSF values   ------------------------------
            if "FWHM_Axial_" in k or "FWHM_Z_ROI" in k:
                # Add the channel do the first layer dict
                ch = k.split("_")[0]
                if ch not in self.individual_data.keys():
                    self.individual_data[ch] = {
                        "FWHM-X": [],
                        "FWHM-Y": [],
                        "FWHM-Z": [],
                    }

                if "_X_" in k:
                    self.individual_data[ch]["FWHM-X"].append(v)
                if "_Y_" in k:
                    self.individual_data[ch]["FWHM-Y"].append(v)
                if "_Z_" in k:
                    self.individual_data[ch]["FWHM-Z"].append(v)

            # Check for shift data (in px)     --------------------------
            # There is no shift averages in the key values
            if "_shift_" in k:
                ch = k.split("_")[0]
                if ch not in self.shift_data.keys():
                    self.shift_data[ch] = {
                        "Shift-X": [],
                        "Shift-Y": [],
                        "Shift-Z": [],
                    }
                if "_X_" in k:
                    self.shift_data[ch]["Shift-X"].append(v)
                if "_Y_" in k:
                    self.shift_data[ch]["Shift-Y"].append(v)
                if "_Z_" in k:
                    self.shift_data[ch]["Shift-Z"].append(v)

        # If FWHM was run on only one channel, this will remain a empty dict
        if len(self.shift_data) > 0:
            # Average the shift values
            for ch, shifts in self.shift_data.items():
                for key, values in shifts.items():
                    if len(values) < 1:
                        raise RuntimeError(
                            "OMERO PSF shift data is missing for: "
                            f"{ch} - {key}"
                        )
                    self.shift_data[ch][key] = self._average_values_(
                        values=values,
                        min_fwhm=-2000,
                    )
            # Include the reference channel for the shifts
            ref_ch = []
            for ch in self.individual_data.keys():
                if ch not in self.shift_data.keys():
                    ref_ch.append(ch)
            if len(ref_ch) != 1:
                raise RuntimeError(
                    "Pixel shift reference channel "
                    f"could not be identified: {ref_ch}"
                )
            self.shift_data[ref_ch[0]] = {
                "Shift-X": "Reference-X",
                "Shift-Y": "Reference-Y",
                "Shift-Z": "Reference-Z",
            }

        # Set the number of channels
        n_av_chs = len(self.average_data.keys())
        n_indi_chs = len(self.individual_data.keys())
        if n_av_chs not in (0, n_indi_chs):
            raise RuntimeError(
                "OMERO data PSF data has values for "
                f"{n_indi_chs} channels, but {n_av_chs} "
                "channels for averaged values..."
            )
        self.n_channels = n_indi_chs

    def _get_metadata_(self):
        """Set the acquisition_date, NA, and objective."""
        for k, v in self.data.items():
            if k == "ACQUISITION_DATE_NUMBER":
                # Date usually in format = YYYYmmdd
                # If date string is not of proper length
                if len(str(v)) != 8:
                    self.acquisition_date = None
                else:
                    try:
                        # Can parse date to int?
                        # Is date before today?
                        date = int(v)
                        today = int(get_today())
                        if date > today:
                            self.acquisition_date = None
                        else:
                            self.acquisition_date = v
                    except ValueError:
                        self.acquisition_date = None
            if k == "OBJECTIVE_MAGNIFICATION":
                # Parse the string (e.g. "20x") to int
                obj = v
                try:
                    obj = int(obj.strip("x"))
                    if obj == 0:
                        self.objective = None
                    else:
                        self.objective = obj
                except ValueError:
                    self.objective = None
            if k == "OBJECTIVE_NA":
                try:
                    na = float(v)
                    if na == 0:
                        self.na = None
                    else:
                        self.na = float(v)
                except ValueError:
                    self.na = None
