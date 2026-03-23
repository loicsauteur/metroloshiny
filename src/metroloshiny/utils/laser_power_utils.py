import pandas as pd
from typing import Union, Optional



def get_linearity(df: pd.DataFrame, date: str, rename_cols: bool = False) -> pd.DataFrame:
    # FIXME unused
    df = df.pivot(index=df.columns[1], columns=df.columns[0], values=date)
    # ensure that the header are all strings
    if rename_cols:
        df.columns = [str(x) + "nm" for x in df.columns]
    return df

    

def wavelength_to_color(w: Union[int, str]):
    # FIXME unused
    # Make sure to work with a number (remove 'nm')
    if isinstance(w, str):
        w = w.split("nm")[0].strip()
        try:
            w = int(w)
        except Exception as e:
            print("Could not convert str to int:", e)
    
    print(w, type(w))
    # Convert wavelength to RGB
    if 380 <= w <= 440:
        r, g, b = -(w - 440) / (440 - 380), 0.0, 1.0
    elif 440 < w <= 490:
        r, g, b = 0.0, (w - 440) / (490 - 440), 1.0
    elif 490 < w <= 530:
        r, g, b = 0.0, 1.0, -(w - 530) / (530 - 490)
    elif 530 < w <= 580:
        r, g, b = (w - 510) / (580 - 530), 1.0, 0.0
    elif 580 < w <= 645:
        r, g, b = 1.0, -(w - 645) / (645 - 580), 0.0
    elif 645 < w <= 750:
        r, g, b = 1.0, 0.0, 0.0
    else:
        r, g, b = 0.0, 0.0, 0.0
    
    # intensity correction
    if 380 <= w <= 420:
        factor = 0.3 + 0.7*(w - 380)/(420 - 380)
    elif 420 < w <= 645:
        factor = 1.0
    elif 645 < w <= 750:
        factor = 0.3 + 0.7*(750 - w)/(750 - 645)
    else:
        factor = 0.0
    
    gamma = 0.8
    r = (r * factor) ** gamma
    g = (g * factor) ** gamma
    b = (b * factor) ** gamma
    return (r, g, b)

   
def get_power_over_time_data(
        df: pd.DataFrame,
        line: Optional[int] = None,
        power_prct: Optional[int] = None,
        merge: bool = True,
        ) -> pd.DataFrame:
    # basically, from original df, get the power of a single line at single % level over dates
    
    # Select only a specific laser line
    if line:
        df = df[df[df.columns[0]] == line]
    
    # Select only a specifc percentage
    if power_prct:
        df = df[df[df.columns[1]] == power_prct]
    
    # Merge the Line and Power columns
    df["Line [nm] @ [%]"] = df[df.columns[0]].astype(str) + " @ " + df[df.columns[1]].astype(str)
    
    # Drop the two columns that were merged
    #df = df.drop(columns=df.columns[:2])
    
    # Reorder columns (last to first)
    if merge:
        cols = list(df)
        cols.insert(0, cols.pop(cols.index(cols[-1])))
        df = df.loc[:, cols]

        # Pivot the table
        df = df.melt(
            id_vars=df.columns[:3],
            var_name="Date",
            value_name="mW"
        )
    else:
        raise NotImplementedError("not yet implemented")
    return df

if __name__ == "__main__":
    from metroloshiny.utils.read_file import read_xlsx
    raw_df = read_xlsx()

    print(get_power_over_time_data(raw_df, 405, 100))

    #df = get_linearity(raw_df, str(20240109))

    

