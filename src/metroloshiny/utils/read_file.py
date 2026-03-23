import pandas as pd
import os
import math
import gspread

import numpy as np

file = './data/deepsim_only.xlsx'

def read_xlsx(file: str = file):
    # Read the xlsx
    df = pd.read_excel(file)
    # Ensue that it is a laser powerment meausrement
    loc_line = None

    # Loop over rows as simple tuples
    for row in df.itertuples(name=None):
        for i, element in enumerate(row):
            if isinstance(element, str) and "Laser" in element:
                #print("col=", i, "==", row)
                # row index can be found at the first position of the row-tuple
                # add 1 to the row, since it is excluding the current header line...
                df = read_laserpower_xlsx_hebel(df=df, header_row=row[0])
                return df

    

    #loc_line = xlsx_df.str.contains(r'Line', na=True)
    #print(xlsx_df[1])
    #print(loc_line)
    #print(df)

def read_laserpower_xlsx_hebel(df: pd.DataFrame, header_row: int) -> pd.DataFrame:
    # Used to reorder the dataframe - basically to skip the unnecessary first rows...

    #print("Before df reorganization...")
    #print(df.head(7))
    #print("--------------------")

    # copy "Line..." and "Power..." to the future header line
    #print("header row =", header_row)
    #print("replacing:", df.iloc[header_row, 0], "with", df.iloc[header_row + 1, 0])
    #print("replacing:", df.iloc[header_row, 1], "with", df.iloc[header_row + 1, 1])
    df.iloc[header_row, 0] = df.iloc[header_row + 1, 0]
    df.iloc[header_row, 1] = df.iloc[header_row + 1, 1]

    # Reset the column index
    df.columns = df.iloc[header_row]
    # drop rows above (and including header row and the row after it)
    df = df[header_row + 2:]
    df.reset_index(drop=True, inplace=True)

    #print("--------------------")
    # Fill empty laser power entries
    cur_laser = None
    for row in df.itertuples():
        if math.isnan(row[1]):
            if cur_laser is None:
                raise RuntimeError("Could not specify laser line for row {row[0]}")
            else:
                df.iloc[row[0], 0] = cur_laser

        else:
            cur_laser = row[1]
        
    # Drop all Nan columns
    df.dropna(axis=1, how="all", inplace=True)
    
    # Make sure we work with numeric values (when errors, leave as is ('ignore'))
    for col in df.columns[2:]:
        extracted = df[col].astype(str).str.extract(r'([-+]?\d*\.?\d+)')[0]
        converted = pd.to_numeric(extracted, errors='coerce')
        # Find failures: original not null but converted is null
        mask = df[col].notna() & converted.isna()
        
        if mask.any():
            print(f"\nColumn '{col}' - failed to convert:")
            print(df.loc[mask, col])
    
        df[col] = converted

    # Rename the df columns (header)
    df.columns = [str(x) for x in list(df.columns)]

    #print("--------------------")
    #print(df)
    return df

def get_private_data(key: str, data_path: str = None) -> str:
    # To read 'private' data (csv with key value pairs)
    # excepts the file ./data/private_data.csv, if not specified with data_path
    # Load csv with Key column as index column
    if data_path is None:
        df = pd.read_csv("./data/private_data.csv", index_col="Key")
    else:
        df = pd.read_csv(data_path, index_col="Key")
    # Get the value row, and take the first (Value) column
    value = df.loc[key].iloc[0]
    # Return a string
    return str(value)

def load_gspread(
        gsheet_url: str,
        sheet_name: str,
        data_path: str = None,
        path_service_account: str = None,
        api_key: str = None
    ) -> gspread.worksheet:
    # Currently the api key is not used (only for viewing public gsheets)
    if api_key is None:
        api_key = get_private_data("Google API Key", data_path=data_path)

    if path_service_account is None:
        gc = gspread.service_account()
    else:
        gc = gspread.service_account(path_service_account)
    #gc = gc.api_key(api_key) # currently not used...

    # Open the sheet with URL
    sh = gc.open_by_url(gsheet_url)
    #sh = gc.open_by_key(sheet_key)
    
    #print("worksheet names:", sh.worksheets())
    return sh.worksheet(sheet_name)

def get_laser_power_objective_data(data_path: str = None):
    # Load laod google sheet with laser power at objective data
    url = get_private_data("Sheet URL", data_path=data_path)
    path_sa = get_private_data("PathToServiceAccountJSON", data_path=data_path)
    sheet = load_gspread(
        gsheet_url=url,
        sheet_name="laser_power_objective_measurements",
        path_service_account=path_sa
    )
    return sheet, pd.DataFrame(sheet.get_all_records())


if __name__ == "__main__":
    # Testing xlsx loading ########
    #print(file, "exists =", os.path.exists(file))
    #df_ = read_xlsx(file)
    #p = list(df_[df_.columns[0]])
    
    #print(df_)
    #p = np.unique(np.asarray(p))
    
    #print(df_.loc[df_["Line [nm]"].isin("405")])

    #df_ = df_.loc[df_[df_.columns[0]] == 405]
    #df_.columns = list(df_.columns)
    #print(df_)

    #print(df_.loc[df_[df_.columns[0]] == 405])

    sheet, df = get_laser_power_objective_data()
    print(df.head())
