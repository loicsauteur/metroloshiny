"""Class for Field Uniformity and Distortion data."""

from typing import Optional

import numpy as np
import pandas as pd
from omero.gateway import BlitzGateway

from metroloshiny.utils.common_utils import point_2d_point_distance
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

    FIXME: not tested on dates that have missing channel(s).

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
        base_df = base_df.dropna(axis="columns", how="all")
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
    def get_channel_names(self, date: str) -> list[str]:
        """
        Getter for channels for a specific date.

        :return: list[str], of channels or empty
        """
        try:
            return list(self._map_channel_names_(date).values())
        except KeyError:
            return []

    def get_distortion(self) -> dict[str, Optional[pd.DataFrame]]:
        """
        Getter for the distortion data.

        :return: dict of str date with pd.DataFrame
            DataFrame with columns: Ring_ID & Channels
        """
        if not self.distortion_tables:
            raise RuntimeError("Distortion data is not set yet.")
        return self.distortion_tables

    def get_uniformity(self) -> dict[str, Optional[pd.DataFrame]]:
        """
        Getter for the uniformity data.

        :return: dict of str date with pd.DataFrame
            DataFrame with columns: Ring_ID & Channels
        """
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

    def get_heat_map_dataframe(
        self, date: str, data_dict: dict[str, pd.DataFrame], test: bool = False
    ) -> pd.DataFrame:
        """
        Create heat-map dataframe for a date and a metric (distortion or uniformity).

        Calculates also the missing middle value (4-connected (+) average)

        :param date: str, date to create the heatmap for
        :param data_dict: e.g. distortion_tables or uniformity_tables
        :param test: bool, option only for testing. Should always be Default = False

        :return: pd.DataFrame, with columns:
            - Ring_ID,
            - Channels* values
            - X (1-based tile index)
            - Y (1-based tile idnex)
        """
        if not data_dict:
            raise RuntimeError("The OMERO data seems not to be loaded yet.")
        # Check
        if date not in data_dict.keys():
            raise ValueError(
                f"There is no data associated with the date {date}."
            )
        if not test and date not in self.roi_detected.keys():
            raise RuntimeError(f"There is no ROI information for date {date}.")

        if not test:
            # Calculate the number of XY tiles
            x, y = self.get_field_of_rings_grid_size(date=date)

            # Get the ROIs
            rois = self.roi_detected.get(date)
            if x * y == len(rois):
                # There is no missing ring!
                raise RuntimeError(
                    f"Expected a missing center ROI. There are {x} X & {y} Y "
                    f"tiles = {x * y}, and {len(rois)} detected rings!"
                )
        else:
            # Specific XY tiles for test
            x = 5
            y = 5

        # Calculate the middle position(s)
        df = data_dict.get(date).copy()
        # Quick check
        if "Ring_ID" not in df.columns:
            raise KeyError(
                f"Expected an 'Ring_ID' column, found only: {df.columns}"
            )

        # Calculate the middle tile (also for non-square field of rings)
        middleTile = x * (y // 2) + x // 2  # 0-based index
        # middleValues = [middleTile + 1] # like a row: Ring_ID, ch-middle-values
        middleValues = {"Ring_ID": [middleTile + 1]}
        for col in df.columns[1:]:
            col_ids = df.columns.get_loc(col)
            average = df.iloc[middleTile - x, col_ids]
            average = average + df.iloc[middleTile - 1, col_ids]
            average = average + df.iloc[middleTile, col_ids]
            average = average + df.iloc[middleTile + x - 1, col_ids]
            average = average / 4
            # middleValues.append(average)
            middleValues[col] = [average]

        before = df.iloc[:middleTile]
        middle = pd.DataFrame().from_dict(middleValues)
        after = df.iloc[middleTile:]
        after = after.copy()
        after["Ring_ID"] = after["Ring_ID"] + 1
        df_out = pd.concat([before, middle, after], ignore_index=True)

        # Add columns for X and Y positions (1-based)
        x_arr = [i for _ in range(y) for i in range(1, x + 1)]
        y_arr = [i for i in range(1, y + 1) for _ in range(x)]

        df_out["X"] = x_arr
        df_out["Y"] = y_arr

        return df_out

    def get_distortion_dataframe(self, date: str) -> pd.DataFrame:
        """
        Create distortion dataframe for visualisation.

        Per ring AND channel get ∆x, ∆y, and magnitude (absolute distance).
        Averages in 4-connected manner the middle (missing) ring.

        :raises:
            RuntimeError if:
            - OMERO data is not loaded (i.e. self.distortion_tables is empty)
            - If there is no missing middle ring (x * y -1 != detected rings)
            NotImplementedError if:
            - No missing middle ring (even number of XY tiles)
            ValueError if:
            - the date has no associated distortion table

        :param date: str, date to calculate the df from

        :return: pd.DataFame with columns:
            - Ring_ID, Channel, x, y, dx, dy, magnitude
        """
        # Sanity checks
        if not self.distortion_tables:
            raise RuntimeError("The OMERO data seems not to be loaded yet.")
        if date not in self.distortion_tables.keys():
            raise ValueError(
                f"The date <{date}> does not have a distortion table."
            )

        # Get the number of x and y tiles calculated from the detected ROI locations
        n_x, n_y = self.get_field_of_rings_grid_size(date=date)
        df = pd.DataFrame(self.distortion_tables.get(date))

        if n_x * n_y - 1 != len(df):
            raise RuntimeError(
                f"Expected a missing center ROI. There are {n_x} X & {n_y} Y "
                f"tiles = {n_x * n_y}, and {len(df)} detected rings!"
            )
        if n_x * n_y % 2 == 0:
            raise NotImplementedError(
                "Only implemented for center Ring missing!"
            )

        # Get the middle index using tile numbers (supports non-square field of rings)
        middle_idx = n_x * (n_y // 2) + n_x // 2 + 1  # 1-based index

        # Idxs for 4-connected Rings before adding middle
        fours = [
            middle_idx - n_x,
            middle_idx - 1,
            middle_idx,
            middle_idx + n_x - 1,
        ]

        # Get a list of the available channels
        # Example columns: Ring_ID, DAPI, DAPI_dx, DAPI_dy, 488, 488_dx, 488_dy, Alexa 647, Alexa 647_dx, Alexa 647_dy
        chs = [x for x in df.columns if "_" not in x]

        # Initialise the final dataframe
        df_final = pd.DataFrame()
        # Create channel dataframes
        for ch in chs:
            # Create dict for final dataframe per channel
            df_dict = {
                "Ring_ID": [],
                "Channel": [ch] * (len(df) + 1),
                "x": [],  # tile position
                "y": [],
                "dx": [],
                "dy": [],
                "Magnitude": [],
            }
            # Get the values that need to be averaged
            dxs = [
                df.loc[df["Ring_ID"] == f, f"{ch}_dx"].iloc[0] for f in fours
            ]
            dys = [
                df.loc[df["Ring_ID"] == f, f"{ch}_dy"].iloc[0] for f in fours
            ]
            dxs = np.average(dxs)
            dys = np.average(dys)
            # Calculate the middle magnitude from their ∆x & ∆y (don't average the 4 individual ones)
            magnitudes = (dxs**2 + dys**2) ** 0.5

            # Initialise the tile positions
            x_tile = 1
            y_tile = 1
            # Loop over the rows in the dataframe
            for _idx, row in df.iterrows():
                # Get the current Ring ID
                cur_ring = int(row["Ring_ID"])
                # Adjust XY tiles according to new rows
                if x_tile > n_x:
                    x_tile = 1
                    y_tile = y_tile + 1
                # Add the middle index
                if cur_ring == middle_idx:
                    df_dict["Ring_ID"].append(cur_ring)
                    df_dict["x"].append(x_tile)
                    df_dict["y"].append(y_tile)
                    df_dict["dx"].append(dxs)
                    df_dict["dy"].append(dys)
                    df_dict["Magnitude"].append(magnitudes)
                    # Update x-tile counter
                    x_tile = x_tile + 1
                # After middle: increase cur_ring by 1
                if cur_ring >= middle_idx:
                    cur_ring = cur_ring + 1

                # Add row as
                df_dict["Ring_ID"].append(cur_ring)
                df_dict["x"].append(x_tile)
                df_dict["y"].append(y_tile)
                df_dict["dx"].append(row[f"{ch}_dx"])
                df_dict["dy"].append(row[f"{ch}_dy"])
                df_dict["Magnitude"].append(row[ch])
                # Increment the x tile count
                x_tile = x_tile + 1

            # Append result to final dict
            if df_final.empty:
                df_final = pd.DataFrame().from_dict(df_dict)
            else:
                df_final = pd.concat(
                    [df_final, pd.DataFrame().from_dict(df_dict)],
                    ignore_index=True,
                )

        return df_final

    def get_distortion_dataframe_from_rois(self, date: str) -> pd.DataFrame:
        """
        Create distortion dataframe for visualisation.

        Per ring get ∆x, ∆y, and magnitude (absolute distance).
        Averages in 4-connected manner the middle (missing) ring.

        # FIXME this will be deprecated, since I can calculate it by channel from table data

        :param date: str, date to calculate the df from

        :return: pd.DataFame with columns:
            - Ring_ID, x, y, dx, dy, magnitude
        """
        # Sanity checks
        if not self.distortion_tables:
            raise RuntimeError("The OMERO data seems not to be loaded yet.")
        # FIXME probably not necessary! -> but i'd prefer using that for all the channels (TODO)
        # if not date in self.distortion_tables.keys():
        #     raise ValueError(
        #         f"There is no distortion data associated with the date {date}."
        #     )
        if date not in self.roi_ideal.keys():
            raise ValueError(
                f"There are no ideal ROIs associated with the date {date}."
            )
        if date not in self.roi_detected.keys():
            raise ValueError(
                f"There are no detected ROIs associated with the date {date}."
            )

        # Get the ROIs {str(Ring_ID): tuple[x, y]}
        n_x, n_y = self.get_field_of_rings_grid_size(date=date)
        detected = self.roi_detected.get(date)
        ideal = self.roi_ideal.get(date)
        if len(detected) > 999:
            raise NotImplementedError("More than 1000 Rings not supported!")
        if n_x * n_y - 1 != len(detected):
            raise RuntimeError(
                f"Expected a missing center ROI. There are {n_x} X & {n_y} Y "
                f"tiles = {n_x * n_y}, and {len(detected)} detected rings!"
            )
        if n_x * n_y % 2 == 0:
            raise NotImplementedError(
                "Only implemented for center Ring missing!"
            )
        # FIXME this is only for one channel (the last)

        # Get the middle index using tile numbers (supports non-square field of rings)
        middle_idx = n_x * (n_y // 2) + n_x // 2 + 1  # 1-based index

        # Idxs for 4-connected Rings before adding middle
        four_1 = middle_idx - n_x
        four_2 = middle_idx - 1
        four_3 = middle_idx
        four_4 = middle_idx + n_x - 1
        fours = []
        for f in [four_1, four_2, four_3, four_4]:
            cur = []
            cur.append(detected.get(str(f).zfill(3)))
            cur.append(ideal.get(str(f).zfill(3)))
            fours.append(cur)
        # Calculate the average between the x and y coordinates
        x_detected_avg = [x[0][0] for x in fours]
        y_detected_avg = [x[0][1] for x in fours]
        x_ideal_avg = [x[1][0] for x in fours]
        y_ideal_avg = [x[1][1] for x in fours]
        fours_avg = [
            (np.average(x_detected_avg), np.average(y_detected_avg)),
            (np.average(x_ideal_avg), np.average(y_ideal_avg)),
        ]

        # Create dict for final dataframe
        df_dict = {
            # "Channel": ??, not yet (at the end...)
            "Ring_ID": [],
            "x": [],  # tile position
            "y": [],
            "dx": [],
            "dy": [],
            "Magnitude": [],
        }
        # Currently not for channel
        # FIXME continue here -> or better with something else until we have a better Table...
        x_tile = 1
        y_tile = 1
        for k, p_detected in sorted(detected.items()):
            # Calculate vector
            p_ideal = ideal.get(k)
            d_x = p_detected[0] - p_ideal[0]
            d_y = p_detected[1] - p_ideal[1]

            cur_ring = int(k)
            # Adjust XY tiles according to new rows
            if x_tile > n_x:
                x_tile = 1
                y_tile = y_tile + 1
            # Add the middle index
            if cur_ring == middle_idx:
                # add middle element before adding cur_ring as it is
                df_dict["Ring_ID"].append(cur_ring)
                df_dict["x"].append(x_tile)
                df_dict["y"].append(y_tile)
                df_dict["dx"].append(fours_avg[0][0] - fours_avg[1][0])
                df_dict["dy"].append(fours_avg[0][1] - fours_avg[1][1])
                df_dict["Magnitude"].append(
                    point_2d_point_distance(fours_avg[0], fours_avg[1])
                )
                # Update counters
                x_tile = x_tile + 1
            # After middle increase cur_ring by 1
            if cur_ring >= middle_idx:
                cur_ring = cur_ring + 1

            # Add element as is (including middle one)
            df_dict["Ring_ID"].append(cur_ring)
            df_dict["x"].append(x_tile)
            df_dict["y"].append(y_tile)
            df_dict["dx"].append(d_x)
            df_dict["dy"].append(d_y)
            df_dict["Magnitude"].append((d_x**2 + d_y**2) ** 0.5)
            # Increment the x tile count
            x_tile = x_tile + 1

        # Convert dictionary to dataframe
        return pd.DataFrame().from_dict(df_dict)

    def get_field_of_rings_grid_size(self, date: str) -> tuple[float, float]:
        """
        Calculate the number of dtected rings in X and Y.

        With the argolight slide, the middle ring is missing (there's a cross).

        :param date: str, date for the rings

        :return: tuple, ring count in x and y
        """
        # Sanity check
        if date not in self.roi_detected.keys():
            raise ValueError(f"There is no ROI information for date {date}.")

        coords = self.roi_detected.get(date)
        # Get a list of only X and Y coordinates separately
        x = [i[0] for i in coords.values()]
        y = [i[1] for i in coords.values()]

        x_count = 1
        # Count the number of rings on the first row
        for i in range(1, len(x)):
            if x[i] > x[i - 1]:
                x_count += 1
            else:
                break

        y_count = 1
        delta_x = (x[1] - x[0]) / 2
        prev_y = y[0]
        # Count the number of rings on the first column
        for i in range(1, len(y)):
            # Check only the first y coords (allow +/- half ring to ring distance)
            if x[i] > x[0] - delta_x and x[i] < x[0] + delta_x:
                if y[i] > prev_y:
                    y_count += 1
                    prev_y = y[i]

        return x_count, y_count

    def get_distortion_over_time(self) -> pd.DataFrame:
        """
        Calculate average and STD distoriotn per channel per date.

        return: pd.DataFrame with columns:
            Date, ch_name1-AVG, ch_name1-STD, ...
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
            headers.append(ch + "-AVG")
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
                    # Average rounded to 3-digits
                    row[ch + "-AVG"] = round(np.average(date_df[ch]), 3)
                    # STD rounded to 3-digits
                    row[ch + "-STD"] = round(np.std(date_df[ch]), 3)
                # Create a df from the dict and concat with the previous one
                row = pd.DataFrame([row])
                df = pd.concat([df, row], ignore_index=True)
        return df

    def get_distortion_over_time_melt(self) -> pd.DataFrame:
        """
        Get the distortion over time melted.

        Same data but with columns:
            Date, Channel, Average*, STD*

        :return: pd.DataFrame
        """
        df = self.get_distortion_over_time()
        # Change the dataframe layout to have columns: date, channel, avg, std
        avg_df = df.melt(
            id_vars="Date",
            value_vars=[c for c in df.columns if c.endswith("-AVG")],
            var_name="Channel",
            value_name="Average Distortion [um]",
        )
        # Remove -AVG from channel names
        avg_df["Channel"] = avg_df["Channel"].str.replace(
            "-AVG", "", regex=False
        )
        # Same also for STD
        std_df = df.melt(
            id_vars="Date",
            value_vars=[c for c in df.columns if c.endswith("-STD")],
            var_name="Channel",
            value_name="STD Distortion",
        )
        std_df["Channel"] = std_df["Channel"].str.replace(
            "-STD", "", regex=False
        )

        # Combine the two dataframes
        df_long = avg_df.merge(std_df, on=["Date", "Channel"])
        return df_long

    def get_uniformity_over_time(self) -> pd.DataFrame:
        """
        Calculate average and STD uniformity per channel per date.

        return: pd.DataFrame with columns:
            Date, ch_name1-AVG, ch_name1-STD, ...
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
            headers.append(ch + "-AVG")
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
                    # Average rounded to 1-digits
                    row[ch + "-AVG"] = round(np.average(date_df[ch]), 1)
                    # STD rounded to 1-digits
                    row[ch + "-STD"] = round(np.std(date_df[ch]), 1)
                # Create a df from the dict and concat with the previous one
                row = pd.DataFrame([row])
                df = pd.concat([df, row], ignore_index=True)
        return df

    def get_uniformity_over_time_melt(self) -> pd.DataFrame:
        """
        Get the uniformity over time melted.

        Same data but with columns:
            Date, Channel, Average*, STD*

        :return: pd.DataFrame
        """
        df = self.get_uniformity_over_time()
        # Change the dataframe layout to have columns: date, channel, avg, std
        avg_df = df.melt(
            id_vars="Date",
            value_vars=[c for c in df.columns if c.endswith("-AVG")],
            var_name="Channel",
            value_name="Average Uniformity [AU]",
        )
        # Remove -AVG from channel names
        avg_df["Channel"] = avg_df["Channel"].str.replace(
            "-AVG", "", regex=False
        )
        # Same also for STD
        std_df = df.melt(
            id_vars="Date",
            value_vars=[c for c in df.columns if c.endswith("-STD")],
            var_name="Channel",
            value_name="STD Uniformity",
        )
        std_df["Channel"] = std_df["Channel"].str.replace(
            "-STD", "", regex=False
        )

        # Combine the two dataframes
        df_long = avg_df.merge(std_df, on=["Date", "Channel"])
        return df_long

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
                    if "_" in col:
                        # col e.g. = ch0_dx
                        ch_name = col.split("_")[0]
                    else:
                        # col e.g. = ch0
                        ch_name = col
                    if ch_name not in ch_map.keys():
                        raise ValueError(
                            f"Cannot match <{col}> to a channel name."
                        )
                    # Replace e.g. ch0 with the actual channel name
                    new_cols.append(col.replace(ch_name, ch_map.get(ch_name)))
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
            # Get a list of omeroID (missing ids may be nan)
            # Only consider strings. Missing channels (NaNs) are ignored
            col_ids = [
                str(x).split("_")[0] for x in df[col] if isinstance(x, str)
            ]
            unique = list(np.unique(np.asarray(col_ids)))
            # Error if there is multiple IDs per date
            if len(unique) > 1:
                unique_ids[col] = None
                self.problems.append(f"{col}: ERROR has more than 1 ID.")
            else:
                unique_ids[col] = unique[0]

        return unique_ids
