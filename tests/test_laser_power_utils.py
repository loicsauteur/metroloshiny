import os
import numpy as np
import pandas as pd

from metroloshiny.utils.laser_power_utils import filter_by_column_value


def test_filter_by_column_value():
    # Check if the file is present
    path = "./data/metroloshiny_data.xlsx"
    assert os.path.exists(path), f'Could not find: {path}'
    
    df = pd.read_excel("./data/metroloshiny_data.xlsx")
    result = len(filter_by_column_value(df, "Microscope", "Ti2 Righty"))
    assert result == 25, f'Expected 25, but got {result}'
