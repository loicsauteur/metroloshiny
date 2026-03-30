import os
import numpy as np
import pandas as pd

from metroloshiny.utils.laser_power_utils import filter_by_column_value, parse_dates


def test_filter_by_column_value():
    # Check if the file is present
    path = "./data/metroloshiny_data.xlsx"
    assert os.path.exists(path), f'Could not find: {path}'
    
    df = pd.read_excel(path)
    result = len(filter_by_column_value(df, "Microscope", "Ti2 Righty"))
    assert result == 25, f'Expected 25, but got {result}'

def test_parse_dates():
    # Check if the file is present
    path = "./data/metroloshiny_data.xlsx"
    assert os.path.exists(path), f'Could not find: {path}'

    import random
    df = pd.read_excel(path)
    # Extract dates and make sure it is all strings
    dates = [str(d) for d in df.columns[7:]]
    # Shuffle the list
    random.shuffle(dates)
    new_dates = parse_dates(dates=dates)

    # Make sure that the dates are in the correct format
    for date in new_dates:
        assert is_valid_yyyymmdd(date), f'Date <{date}> is not a valid date YYYYMMDD'
    
    # Make sure that the dates are ordered properly
    for i in range(1, len(new_dates)):
        assert int(new_dates[i-1]) <= int(new_dates[i]), f'{new_dates[i-1]} is not <= {new_dates[i]}'

    # Sanity tests
    assert not is_valid_yyyymmdd("20262312")
    assert not is_valid_yyyymmdd("20220210-1")


def is_valid_yyyymmdd(date: str) -> bool:
    """
    Check if a string is a date in format YYYYMMDD.

    :param date: str date

    :return: boolean whether a valid date or not.
    """
    from datetime import datetime
    try:
        datetime.strptime(date, "%Y%m%d")
        return True
    except ValueError:
        return False


if __name__ == "__main__":
    test_parse_dates()