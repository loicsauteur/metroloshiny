"""Class for Field Uniformity and Distortion data."""

from typing import Optional

import numpy as np
import pandas as pd
from omero.gateway import BlitzGateway

from metroloshiny.utils.omero_utils import (
    get_cred,
    get_omero_ring_rois,
    get_omero_table,
)


class FieldData:
    """
    Class that represents Fild uniformity & distortion over time.

    Tries to be flexible, i.e. if there are problems (e.g. a OMERO ID does not exist anymore),
    it will still try to get some date. And at the same time it will populate a "log" list
    (a list of strings; variable name = problems).

    """

    def __init__(self, base_df: pd.DataFrame, retrieve_omero: bool = True):
        """
        Initialise the FieldData object from a DataFrame.

        :param base_df: pd.Dataframe
            with columns:
                - "Channel": Channel name to be displayed (**all str**)
                - "Dates": measurements dates
            The date values are e.g. "omero34545454_ch-0":
                indicating:
                    - the origin (omero)
                    - the image ID
                    - the omero channel to be associated with the display channel
        :param get_from_omero: bool, if True retrieves data from OMERO
        """
        # Make sure that there are not nan columns in the input dataframe
        base_df = base_df.replace("", np.nan)
        base_df = base_df.dropna(axis="columns")
        # Make sure the Channels are all str
        base_df["Channel"] = base_df["Channel"].astype(str)
        self.base_df = base_df

        self.channel_names = list(base_df["Channel"])

        # Initialise the data dictionaries      ---------------------
        # Distortion tables {str(date): omero_table dataframe}
        self.distortion_tables = {}
        # Uniformity tables {str(date): omero_table dataframe}
        self.uniformity_tables = {}
        # Roi information dict {str(date): {str(roiID): (centroid )} }
        self.roi_detected = {}
        self.roi_ideal = {}

        # To keep track of errors/problems
        self.problems = []

        # Set the data
        if retrieve_omero:
            self._set_data_()

    # Getters/Setters           ##############################################
    def get_distortion(self) -> dict[str, Optional[pd.DataFrame]]:
        """Getter for the distortion data."""
        if not self.distortion_tables:
            raise RuntimeError("Distortion data is not set yet.")
        return self.distortion_tables

    def get_uniformity(self) -> dict[str, Optional[pd.DataFrame]]:
        """Getter for the uniformity data."""
        if not self.uniformity_tables:
            raise RuntimeError("Uniformity data is not set yet.")
        return self.uniformity_tables

    def get_detected_rois(
        self,
    ) -> dict[str, Optional[dict[str, tuple[float, float]]]]:
        """Getter for the detected ROIs."""
        if not self.roi_detected:
            raise RuntimeError("Detected ROI data is not set yet.")
        return self.roi_detected

    def get_ideal_rois(
        self,
    ) -> dict[str, Optional[dict[str, tuple[float, float]]]]:
        """Getter for the ideal ROIs."""
        if not self.roi_ideal:
            raise RuntimeError("Ideal ROI data is not set yet.")
        return self.roi_ideal

    # Functions for data visualisation      ##################################

    def get_distortion_over_time(self) -> pd.DataFrame:
        """
        Calculate average and STD distoriotn per channel per date.

        return: pd.DataFrame with columns:
            Date, ch_name1, ch_name1-STD, ...
        """
        # Use getter to make sure the data is set
        try:
            data = self.get_distortion()
        except RuntimeError:
            # Force getting the data from OMERO
            self._set_data_()
            data = self.get_distortion()

        # Sanity test
        if not data:
            raise RuntimeError(
                "Something is awfully wrong... probably there is no date entries."
            )

        headers = ["Date"]
        for ch in self.channel_names:
            headers.append(ch)
            headers.append(ch + "-STD")
        df = pd.DataFrame(columns=headers)

        for date, date_df in sorted(data.items()):
            if date_df is None:
                # Add date row with NaNs
                df.loc[len(df)] = {"Date": date}
            else:
                # Create a dict for a row
                row = {"Date": date}
                for ch in date_df.columns[1:]:
                    row[ch] = np.average(date_df[ch])
                    row[ch + "-STD"] = np.std(date_df[ch])
                # Create a df from the dict and concat with the previous one
                row = pd.DataFrame([row])
                df = pd.concat([df, row], ignore_index=True)
        return df

    def get_uniformity_over_time(self) -> pd.DataFrame:
        """
        Calculate average and STD uniformity per channel per date.

        return: pd.DataFrame with columns:
            Date, ch_name1, ch_name1-STD, ...
        """
        # Use getter to make sure the data is set
        try:
            data = self.get_uniformity()
        except RuntimeError:
            # Force getting the data from OMERO
            self._set_data_()
            data = self.get_uniformity()

        # Sanity test
        if not data:
            raise RuntimeError(
                "Something is awfully wrong... probably there is no date entries."
            )

        headers = ["Date"]
        for ch in self.channel_names:
            headers.append(ch)
            headers.append(ch + "-STD")
        df = pd.DataFrame(columns=headers)

        for date, date_df in sorted(data.items()):
            if date_df is None:
                # Add date row with NaNs
                df.loc[len(df)] = {"Date": date}
            else:
                # Create a dict for a row
                row = {"Date": date}
                for ch in date_df.columns[1:]:
                    row[ch] = np.average(date_df[ch])
                    row[ch + "-STD"] = np.std(date_df[ch])
                # Create a df from the dict and concat with the previous one
                row = pd.DataFrame([row])
                df = pd.concat([df, row], ignore_index=True)
        return df

    # Functions for data setting           ###################################

    def _map_channel_names_(self, date: str) -> dict[str, str]:
        """
        Map OMERO channel to channel name.

        :param date: str, date for the omero channels

        :return: dict, {omero ch: channel name}
        """
        channel_df = self._get_channel_name_dataframe_()
        # Sanity check
        if date not in channel_df.columns:
            raise KeyError(
                f"Date <{date}> is not available in the data ({list(channel_df.columns)})."
            )
        channel_map = {}
        for _idx, row in channel_df.iterrows():
            channel_map[row[date]] = row["Channel"]
        return channel_map

    def _update_channel_names_(self):
        """Update the channel names in distoriton/uniformity dataframes."""
        # Adjust the distortion data
        for date, df in self.distortion_tables.items():
            # Get the channel name mapping
            ch_map = self._map_channel_names_(date=date)
            if df is not None:
                # "Cast" to dataframe
                _df = pd.DataFrame(df)
                # First column stays the same
                new_cols = [_df.columns[0]]
                for col in _df.columns[1:]:
                    if col not in ch_map.keys():
                        raise ValueError(
                            f"Cannot match <{col}> to a channel name."
                        )
                    new_cols.append(ch_map.get(col))
                # Set the new column names
                _df.columns = new_cols
                # Overwrite the data dict (necessary!)
                self.distortion_tables[date] = _df

        # Adjust the unifomity data
        for date, df in self.uniformity_tables.items():
            # Get the channel name mapping
            ch_map = self._map_channel_names_(date=date)
            if df is not None:
                # "Cast" to dataframe
                _df = pd.DataFrame(df)
                # First column stays the same
                new_cols = [_df.columns[0]]
                for col in _df.columns[1:]:
                    if col not in ch_map.keys():
                        raise ValueError(
                            f"Cannot match <{col}> to a channel name."
                        )
                    new_cols.append(ch_map.get(col))
                # Set the new column names
                _df.columns = new_cols
                # Overwrite the data dict (necessary!)
                self.uniformity_tables[date] = _df

    def _set_data_(self):
        """
        Set the uniformity, distortion, detected and ideal roi dictionaries.

        Each dict has
            key = date,
            value = table/roi-dict,
                or value = None if something goes wrong
        """
        # Init the result dictionaries
        dist_dict = {}
        unif_dict = {}
        roi_detected_dict = {}
        roi_ideal_dict = {}
        unique_ids = self._get_unique_image_ids_()
        # Collect all OMERO IDs and File IDs separately
        omero_ids = {}
        file_ids = {}
        for date, v in unique_ids.items():
            if v is None:
                dist_dict[date] = None
                unif_dict[date] = None
                roi_detected_dict[date] = None
                roi_ideal_dict[date] = None
            elif v.startswith("omero"):
                try:
                    omero_ids[date] = int(v.replace("omero", ""))
                except ValueError:
                    # print(f"OMERO ID <{v}> for date {date} could not be parsed.")
                    self.problems.append(
                        f"{date}: ERROR {v} OMERO ID could not be parsed."
                    )
            elif v.startswith("file"):
                try:
                    file_ids[date] = int(v.replace("file", ""))
                except ValueError:
                    # print(f"File ID <{v}> for date {date} could not be parsed.")
                    self.problems.append(
                        f"{date}: ERROR {v} File ID could not be parsed."
                    )
            else:
                raise ValueError(f"OMERO/file ID <{v}> invalid!")

        # Get the data from OMERO
        try:
            usr, pwd, host, port = get_cred()
            conn = BlitzGateway(
                username=usr, passwd=pwd, host=host, port=port, secure=True
            )
            conn.connect()

            for date, image_id in omero_ids.items():
                try:
                    dist_df = get_omero_table(
                        conn, image_id, "Field_distortion"
                    )
                    unif_df = get_omero_table(
                        conn, image_id, "Field_uniformity"
                    )
                    det_roi, ideal_roi = get_omero_ring_rois(conn, image_id)
                    dist_dict[date] = dist_df
                    unif_dict[date] = unif_df
                    roi_detected_dict[date] = det_roi
                    roi_ideal_dict[date] = ideal_roi
                except Exception as err:
                    # if exception, then something went wrong (e.g. ID is missing)
                    dist_dict[date] = None
                    unif_dict[date] = None
                    roi_detected_dict[date] = None
                    roi_ideal_dict[date] = None
                    self.problems.append(
                        f"{date}: Error could not get data from OMERO ({err})."
                    )
        finally:
            conn.c.closeSession()

        # Get the data from File FIXME to be implemented
        for date, _v in file_ids.items():
            # Currently set results to None
            dist_dict[date] = None
            unif_dict[date] = None
            roi_detected_dict[date] = None
            roi_ideal_dict[date] = None
            # print(f"Reading from file (for date {date}) is not implemented.")
            self.problems.append(f"{date}: NotImplemented reading from file.")

        # Check for missing dates and set the values to None
        for date in unique_ids.keys():
            if date not in dist_dict.keys():
                dist_dict[date] = None
            if date not in unif_dict.keys():
                unif_dict[date] = None
            if date not in roi_detected_dict.keys():
                roi_detected_dict[date] = None
            if date not in roi_ideal_dict.keys():
                roi_ideal_dict[date] = None

        # Set the class variables
        self.distortion_tables = dist_dict
        self.uniformity_tables = unif_dict
        self.roi_detected = roi_detected_dict
        self.roi_ideal = roi_ideal_dict

        # Update/match the channel names
        self._update_channel_names_()

    def _get_channel_name_dataframe_(self) -> pd.DataFrame:
        """
        Match the channel column to the omero channel name.

        :return: pd.DataFrame, same as input but the IDs removed
        """
        df = self.base_df.copy()
        for col in df.columns[1:]:
            # Remove ID info, & convert ch-1 to ch1
            df[col] = (
                df[col].astype(str).str.split("_").str[1].str.replace("-", "")
            )
        return df

    def _get_unique_image_ids_(self) -> dict[str, Optional[str]]:
        """
        Get the unique image IDs.

        # FIXME i am not sure if the _ch-0: will match the OMERO table head (ch0)
        :return: dict, with:
            key = str, date
            value = str, omero/file ID
        """
        df = self.base_df.copy()
        df = df[df.columns[1:]]

        unique_ids = {}
        for col in df.columns:
            # Get a list of omeroID
            col_ids = [str(x).split("_")[0] for x in df[col]]
            unique = list(np.unique(np.asarray(col_ids)))
            # Error if there is multiple IDs per date
            if len(unique) > 1:
                unique_ids[col] = None
                self.problems.append(f"{col}: ERROR has more than 1 ID.")
            else:
                unique_ids[col] = unique[0]

        return unique_ids
