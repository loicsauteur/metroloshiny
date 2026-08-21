"""Reading/handling of csv and xlsx files."""

from datetime import datetime

import pandas as pd

from metroloshiny.utils.dataframe_utils import (
    convert_date_column,
    convert_power_column,
)


def get_power_measurement(path: str) -> tuple[str, pd.DataFrame]:
    """
    Parse supported power measurement files.

    Wrapper function that tries to parse different supported files.

    Currently supported:
        - "Simone's" csv (ThorLabs Optical Parameter Monitor file)
        - "Tom's" xlsx (Custom NIS / JOBS output file)

    :raises: NotImplementedError, if file(s) not in the expected format.
        Or also for other errors...

    :param path: str, path to file

    :return: tuple[str, pd.DataFrame]
        - str, file type output identifier
            - "simpleXLSX" for a simple (manual) xlsx file
            - "nis_job" for Tom's file
            - "thorlabs" for Simone's file
            - TODO others to be implemented
        - DataFrame with columns = ? Line [nm] ?|Power [%]|'Date'
            - For Tom's file there is an additional column "Objective" at the beginning
    """
    # Init some place holders
    df = None
    possible_exception = []
    if path.endswith(".xlsx"):
        # Try reading simple xlsx file
        try:
            df = read_simple_xlsx(path)
            return "simpleXLSX", df
        except Exception as err:
            possible_exception.append(f"Simple XLSX file: {err!s}")
        # Try reading NIS JOB xlsx from Tom
        try:
            df = read_nis_job_xlsx(path)
            return "nis_job", df
        except Exception as err:
            possible_exception.append(f"ThorLabs XLSX file: {err!s}")
        # TODO implement try reading other xlsx files

        # Reading the file is not implemented
        raise NotImplementedError(
            f"The .xlsx file could not be read: {possible_exception}"
        )

    elif path.endswith(".csv"):
        # Try reading Thorlabs csv from Simone
        try:
            df = read_thorlabs_csv(path)
            return "thorlabs", df
        except Exception as err:
            possible_exception = err
        # TODO implement try reading other csv files

        # Eeading the file is not implemented
        raise NotImplementedError(
            f"The .csv file could not be read: {possible_exception}"
        )

    else:
        raise NotImplementedError(f"Your file type is not implemented: {path}")


def read_thorlabs_csv(path: str) -> pd.DataFrame:
    """
    Try reading a thorlabs power measurement file.

    Creates a dataframe similar to the google spread sheet, with columns:
    ["? Line [nm]", "Power [%]", "'the date'"]

    :raises: NotImplementedError, if not csv or file not as expected.

    :param path: str, path to file.

    :return: pd.DataFrame
    """
    # Sanity test
    if not isinstance(path, str):
        raise IOError("Only string paths are supported.")
    # Only support csv files
    if not path.endswith(".csv"):
        raise NotImplementedError(
            "Reading Thorlabs only implemented for CSV files."
        )

    # Try to identify specific elements in the expected csv file
    delimiter = None
    first_line = None
    wavelength = None
    with open(path, mode="r", encoding="utf-8") as file:
        for i, line in enumerate(file):
            # Identify the file delimiter
            if line.startswith("Delimiter Used"):
                delimiter = line.split("'")[1]
            # Find the first data line
            if line.startswith("Samples"):
                first_line = i - 2
                # Needs to be offsetted
            # Find the wavelength used
            if line.startswith("Wavelength"):
                wavelength = line.split(" ")[-2]
                try:
                    wavelength = int(wavelength)
                except ValueError as err:
                    raise RuntimeError(
                        "Could not identify the used Wavelength from: "
                        f"{line}, using <{' '.join(line.split(' ')[-2:])}>"
                    ) from err

    if delimiter is None or first_line is None or wavelength is None:
        raise NotImplementedError(
            "File does not seem to be the expected Thorlabs file."
        )

    # Convert csv to dataframe
    df = pd.read_csv(path, sep=delimiter, header=first_line)
    # Remove "unnamed" columns
    cols = [x for x in df.columns if x.startswith("Unnamed")]
    df = df.drop(columns=cols)
    # Remove the "Time.." column
    cols = [x for x in df.columns if x.startswith("Time")]
    df = df.drop(columns=cols)

    # Convert the date to YYYYmmdd
    df = convert_date_column(df)
    # Convert power measurements to mW
    df = convert_power_column(df)

    # Make the table ~similar~ to the google sheet
    # |   ? Line [nm] ?	|   Power [%]	|   'Date'
    # Get the date as string, then drop the col
    date = str(df.iloc[0, 1])
    df = df.drop(columns=df.columns[1])
    # 2 columns left: "Samples " (-> Power) and "Power" (-> date)
    # Rename columns
    df.columns = ["Power [%]", date]

    # Make the new Power column values "Sample: " + cell value
    df["Power [%]"] = "Sample: " + df["Power [%]"].astype(str)

    # Add the wavelength as first column
    df.insert(0, "? Line [nm]", wavelength)
    return df


def read_simple_xlsx(path: str) -> pd.DataFrame:
    """
    Try reading xlsx file manually generated (power measurements).

    Creates a dataframe similar to the google spread sheet, with columns:
    ["? Line [nm]", "Power [%]", "'the date'"]

    :raises: NotImplementedError, if not xlsx or file not as expected.

    :return: pd.DataFrame
    """
    # Sanity test
    if not isinstance(path, str):
        raise IOError("Only string paths are supported.")
    # Only support csv files
    if not path.endswith(".xlsx"):
        raise NotImplementedError("Not an excel files.")

    # Read the file into pandas
    df = pd.read_excel(path)
    # Check the file
    if df.empty:
        raise NotImplementedError("Empty file.")
    if (
        len(df.columns) != 3
        or "Wavelength" != df.columns[0]
        or "Power" != df.columns[1]
    ):
        raise NotImplementedError("Columns not as expected.")
    if df.columns[2] not in ["nW", "µW", "mW", "W"]:
        raise NotImplementedError(
            f"Measurement unit <{df.columns[2]}> is unknown."
        )
    for col in df.columns:
        if df[col].dtype not in ["int64", "float64"]:
            raise NotImplementedError(f"Data (in column {col}) is not numeric")
    # Do not allow missing values
    if df.isna().any().any():
        raise NotImplementedError("Data contains missing values.")

    # Rename the columns to ensure measurements in mW
    new_cols = ["? Line [nm]", "prct", f"Power ({df.columns[2]})"]
    df.columns = new_cols
    df = convert_power_column(df)

    # Final renaming of the columns
    new_cols = ["? Line [nm]", "Power [%]", "date-missing"]
    df.columns = new_cols
    return df


def read_nis_job_xlsx(path: str) -> pd.DataFrame:
    """
    Try reading xlsx file generated by NIS' JOBS by Tom Lumen.

    Creates a dataframe similar to the google spread sheet, with columns:
    ["Objective","? Line [nm]", "Power [%]", "'the date'"]
    Thus, needs filtering by objective.

    It may also contain multiple date columns, if xlsx sheets have different dates.
    Or a date column: "date-missing" if the date could not be parsed / was missing.

    :raises: NotImplementedError, if not xlsx or file not as expected.

    :param path: str, path to file.

    :return: pd.DataFrame
    """
    # Sanity test
    if not isinstance(path, str):
        raise IOError("Only string paths are supported.")
    # Only support csv files
    if not path.endswith(".xlsx"):
        raise NotImplementedError(
            "Reading NIS JOBs power measurement only implemented for excel files."
        )

    # Read file and determine the number of sheets
    file = pd.ExcelFile(path)
    sheets = file.sheet_names

    # Init place holder for "merged" dataframe
    df_final = pd.DataFrame()

    # Open the full sheet to identify extra info
    for sheet in sheets:
        df = pd.read_excel(file, sheet_name=sheet)
        # Find the power unit (if None -> no measurements for this sheet) ####
        # Find the cell (first col) shtat startswith "All values" to identify unit
        first_col = df.iloc[:, 0]
        info = first_col[
            first_col.astype(str).str.startswith("All values", na=False)
        ]
        info = info.iloc[0] if not info.empty else None
        if info is None:
            # Skip this sheet
            continue
        power_unit = str(info).split(",")[0].split(" ")[-1]

        # Get the Date              ##########################################
        # Date is the column headers (col H / 8th col)
        date = df.columns[7]
        # The date may be read already as date time object
        if str(date).startswith("da"):
            # Date is missing...
            date = "date-missing"
        # If date is already a datetime object - DONT trust it
        # FIXME it is not really reliable how excel writes date formats
        elif isinstance(date, datetime):
            # Reading dateformat may be wrong in most cases (day and month switched)
            # I saw that month and day may be switched
            date = "date-missing"
        else:
            # Convert the date string from dd-mm-yyyy to YYYYmmdd
            # Attention the string format may be different per PC (found dd/mm/YY) currently not checked
            try:
                date = datetime.strptime(date, "%d-%m-%Y").strftime("%Y%m%d")
            except ValueError:
                # Could not parse date (with expected format)
                date = "date-missing"

        # Idnetify the row that starts with "Power"
        row_idx = df.iloc[:, 0].astype(str).str.startswith("Power", na=False)
        row_idx = df.index[row_idx][0] if row_idx.any() else None
        if row_idx is None:
            # Probably the file is wrong!
            raise NotImplementedError(
                "File does not seem to be the expected NIS JOBs file."
            )

        # Identify the objective name
        objective = df.iloc[row_idx - 2, 0]

        # Create the power measurement table        ##########################
        # Get the headers
        headers = list(df.iloc[row_idx + 1])
        headers[0] = "Power [%]"
        # Rename "xxx nm" to "xxx"
        headers = [int(x.split(" ")[0]) if "nm" in x else x for x in headers]

        # Remove unnecessary first rows
        df = df.iloc[row_idx + 1 :]
        # Rename headers, then drop the headers row
        df.columns = headers
        df = df.iloc[1:]
        df = df.reset_index(drop=True)

        # Drop columns that start with "Wavelength"
        cols = [x for x in df.columns if str(x).startswith("Wavelength")]
        df = df.drop(columns=cols)

        # Transpose the df, to have 3 cols (Power, Line, Value/date)
        df = df.melt(
            id_vars="Power [%]",
            var_name="? Line [nm]",
            value_name="Value",  # FIXME should be the date! (also below...)
        )
        # Make sure that the Line values are integers
        df["? Line [nm]"] = df["? Line [nm]"].astype(int)

        # Make sure that the values are floats
        df["Value"] = df["Value"].astype(float)

        # Swap Power and Line columns
        df = df.reindex(columns=["? Line [nm]", "Power [%]", "Value"])

        # Make sure power measurements are in mW
        final_col_names = list(df.columns)
        # Temporary rename of the column headers -> last col = "Power (unit)"
        cols = ["Line", "prct", f"Power ({power_unit})"]
        df.columns = cols
        df = convert_power_column(df)
        # Rename the columns to the previous & change "Value" to the date
        final_col_names[-1] = date
        df.columns = final_col_names

        # Insert an objective column at the first position
        df.insert(0, "Objective", f"{sheet}: {objective}")

        # Merge the dataframes from the different sheets
        df_final = pd.concat([df_final, df])

    # If the final dataframe is empty, nothing could be read. Hence, xlsx file not in expected format
    if df_final.empty:
        raise NotImplementedError(
            "File does not seem to be the expected NIS JOB file."
        )

    return df_final
