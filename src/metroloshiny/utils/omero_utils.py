"""Utils for getting OMERO data."""

from typing import Any, Optional, Union

import pandas as pd
from omero.gateway import (
    BlitzGateway,
    FileAnnotationWrapper,
    MapAnnotationWrapper,
    TagAnnotationI,  # same if imported from omero.model
)

from metroloshiny.utils.common_utils import point_2d_point_distance
from metroloshiny.utils.read_file import get_private_data

# Dictionary matching upload category to metric to look for.
__metrics__ = {
    "PSF": "FWHM",
}

# FIXME: here are several deprecated functions -> TODO clean up!


def get_image_voxelsize_channel_names(
    image_id: int,
    username: Optional[str] = None,
    passwd: Optional[str] = None,
    host: Optional[str] = None,
    port: Optional[int] = None,
    path_private_data: Optional[str] = None,
):
    """
    Get voxel size and channel names for an Image ID.

    :param image_id: int OMERO dataset ID
    :param username: str OMERO user name.
                If None, will get it from private_data.csv
    :param passwd: str OMERO user password.
                If None, will get it from private_data.csv
    :param host: str OMERO host.
                If None, will get it from private_data.csv
    :param port: str OMERO port.
                If None, will get it from private_data.csv
    :param path_private_data: str path to private_data.csv.
                If None takes default path "./data/private_data.csv"

    :return: tuple[
        Optional[list[float]],  XYZ voxel size
        Optional[list[str]],    channel names on OMERO
    ]
    """
    # Get the connection details from file
    username, passwd, host, port = get_cred(
        path_private_data, username, passwd, host, port
    )
    # Init result variables
    channel_names = None
    voxel_size = None

    # Connect to OMERO
    try:
        conn = BlitzGateway(
            username=username, passwd=passwd, host=host, port=port, secure=True
        )
        conn.connect()
        # Get the image channel name list
        channel_names = get_channel_names(
            conn=conn, datatype="Image", id=image_id
        )
        # Get the image voxel sizes
        voxel_size = get_voxel_size(conn=conn, datatype="Image", id=image_id)

    finally:
        conn.c.closeSession()
    # Return results (may be none)
    return voxel_size, channel_names


def get_images_for_metric(
    dataset_id: int,
    metric_id: str,
    username: Optional[str] = None,
    passwd: Optional[str] = None,
    host: Optional[str] = None,
    port: Optional[int] = None,
    path_private_data: Optional[str] = None,
):
    """
    Get images from a dataset which have the metric of interest.

    :param dataset_id: int OMERO dataset ID
    :param metric_id: metric to look for in OMERO.
    :param username: str OMERO user name.
                If None, will get it from private_data.csv
    :param passwd: str OMERO user password.
                If None, will get it from private_data.csv
    :param host: str OMERO host.
                If None, will get it from private_data.csv
    :param port: str OMERO port.
                If None, will get it from private_data.csv
    :param path_private_data: str path to private_data.csv.
                If None takes default path "./data/private_data.csv"

    :return: tuple[dict, dict]
        - dict[int, str] with
            key = image ID
            value = f"image ID: image name"
        - dict[int, pd.DataFrame] with
            key = image ID
            value = key-value table with columns ["Key", "Value"] for OMERO key-value pairs
            # FIXME check/improve for tables...

    """
    # Get the connection details from file
    username, passwd, host, port = get_cred(
        path_private_data, username, passwd, host, port
    )
    # Check the metric value to look for        ##############################
    if metric_id not in __metrics__.values():
        if metric_id not in __metrics__.keys():
            raise NotImplementedError(
                f"The metric <{metric_id}> is not supported."
            )
        try:
            metric_id = str(__metrics__.get(metric_id))
        except Exception as err:
            raise RuntimeError(f"Error: {err!s}") from err

    # Init dict {id: name} for IDs that have metrics
    id_name_dict = {}
    # Init dict {id: df} for IDs that have metrics
    id_df_dict = {}

    # Connect to OMERO
    try:
        conn = BlitzGateway(
            username=username, passwd=passwd, host=host, port=port, secure=True
        )
        conn.connect()

        # Get a dict of all image in dataset {image_id: image_name}
        image_ids = get_images_in_dataset(conn=conn, dataset_id=dataset_id)

        for id, name in image_ids.items():
            cur_data = get_metric_data(
                conn=conn, image_id=id, metric=metric_id
            )
            if isinstance(cur_data, pd.DataFrame):
                id_name_dict[id] = f"{id}: {name}"
                id_df_dict[id] = cur_data
    finally:
        conn.c.closeSession()
    return id_name_dict, id_df_dict


def get_images_in_dataset_by_tag(
    conn: BlitzGateway, dataset_id: int, tag_names: list[str]
) -> dict:
    """
    Get a of all image form a dataset ID by tag annotation matching.

    :param conn: BlitzGateway
    :param dataset_id: int
    :param tag_names: list[str], list of 1 or several tags to select images.

    :return: dict {image_id: image_name}
    """
    # Sanity check
    if not isinstance(tag_names, list):
        raise ValueError("Tag names must be a list of str!")

    dataset = conn.getObject("dataset", dataset_id)
    # Images is None if it is not a dataset ID
    if dataset is None:
        raise RuntimeError(f"<{dataset_id}> does not seem to be a dataset ID.")
    if dataset.countChildren() == 0:
        raise RuntimeError(f"There are no images for dataset: <{dataset_id}>")
    # Get the images form the dataset
    images = dataset.listChildren()

    id_name_dict = {}
    # Check tags in each image
    for img in images:
        # Tags are annotation objects
        anns = img.listAnnotations()
        # Check if all tags in the annotations
        if check_image_tags(anns=anns, tags=tag_names):
            id_name_dict[img.getId()] = img.getName()
    return id_name_dict


def check_image_tags(anns: list, tags: list[str]) -> bool:
    """
    Check if annotation list contains all tags.

    :param anns: list, OMERO Annotations
    :param tags: list[str], tag names to check

    :return: bool, True if all tags in annotation list
    """
    found_tags = []
    # Check each searched tag in the annotations
    for ann in anns:
        if ann.OMERO_TYPE == TagAnnotationI:
            for tag in tags:
                if ann.getTextValue() == tag:
                    found_tags.append(ann.getId())
                    # (Stop => only one tag even if several with the same name)
                    break
    # Return True if all tags found
    return len(found_tags) == len(tags)


def get_images_in_dataset(conn: BlitzGateway, dataset_id: int) -> dict:
    """
    Get a of all image IDs (with their names) for a dataset ID.

    :param conn: BlitzGateway
    :param dataset_id: int

    :return: dict {image_id: image_name}
    """
    dataset = conn.getObject("dataset", dataset_id)
    # Images is None if it is not a dataset ID
    if dataset is None:
        raise RuntimeError(f"<{dataset_id}> does not seem to be a dataset ID.")
    if dataset.countChildren() == 0:
        raise RuntimeError(f"There are no images for dataset: <{dataset_id}>")
    # Get the images form the dataset
    images = dataset.listChildren()

    id_name_dict = {i.getId(): i.getName() for i in images}
    return id_name_dict


def get_cred(
    path_private_data: Optional[str] = None,
    username: Optional[str] = None,
    passwd: Optional[str] = None,
    host: Optional[str] = None,
    port: Optional[int] = None,
) -> tuple:
    """
    Get credentials for OMERO connection from private data.

    :param path_private_data: Optional path to private_data.csv. If None,
                              will search for default location of the file.
    :param username: If None, returns str OMERO USER from private_data.csv.
    :param passwd: If None, returns str OMERO PASSWORD from private_data.csv.
    :param host: If None, returns str OMERO HOST from private_data.csv.
    :param port: If None, returns str OMERO PORT from private_data.csv.

    :return: (username, passwd, host, port)
    """
    if username is None:
        username = get_private_data("OMERO USER", path_private_data)
    if passwd is None:
        passwd = get_private_data("OMERO PASSWORD", path_private_data)
    if host is None:
        host = get_private_data("OMERO HOST", path_private_data)
    if port is None:
        try:
            port = int(get_private_data("OMERO PORT", path_private_data))
        except Exception as err:
            raise RuntimeError(
                "Could not parse private_data.csv OMERO PORT to int."
            ) from err
    return username, passwd, host, port


def omero_table_to_dict(table) -> dict:
    """
    Already loaded OMERO.table to dict.

    TODO check if this works as expected.

    :param table: OMERO table data object (already loaded)

    :return: dict
    """
    n_headers = len(table.getHeaders())
    n_rows = table.getNumberOfRows()
    data = table.read(range(n_headers), start=0, stop=n_rows)
    dict_out = {}
    for col in data.columns:
        if col.name in dict_out.keys():
            raise RuntimeError(
                f"OMERO table contains headers with same name: {col.name}"
            )
        dict_out[col.name] = col.values
    return dict_out


def get_metric_data(
    conn: BlitzGateway, image_id: int, metric: str
) -> Optional[pd.DataFrame]:
    """
    Get the metric data from the OMERO image.

    Finds the first OMERO.table or kv-pair that contains the metric of interest.
    Prefers kv-pair over OMERO.table.
    Checks OMERO.table headers if any of them contain the metric.
    Checks kv pair keys for metric (excludes "Profile_length_for_FWHM")

    :param conn: BlitzGateway
    :param image_id: int, OMERO image ID
    :param metric: str, metric to find, e.g. FWHM

    :return: None, if the metric was not found in the image
        pd.DataFrame
    """
    # Collect all kv-paris and omero.tables
    kv_pairs = []
    tables = []
    # Get Omero image
    image = conn.getObject("image", image_id)
    if image is None:
        raise RuntimeError(f"ID <{image_id} does not seem to be an Image ID.")
    # Loop over annotation objects to get kv-paris or table
    res = conn.c.sf.sharedResources()
    for ann in image.listAnnotations():
        # Check for tables
        if isinstance(ann, FileAnnotationWrapper):
            try:
                # It's a table if it can be opened
                table = res.openTable(ann.getFile()._obj)
                tables.append(table)
            except Exception:
                # Not a table - skip
                pass
        elif isinstance(ann, MapAnnotationWrapper):
            kv_pairs.append(ann.getValue())

    # Check if the metric of interest is somewhere
    final_kv_pair = None
    final_table = None

    # Get the first table that has the metric
    for table in tables:
        for col in table.getHeaders():
            if metric in col.name:
                final_table = table
                break

    # Get the first kv-pair that contains the metric
    for kv in kv_pairs:
        # loop over the tuples of length 2,
        for k, _v in kv:
            # Check if the first item (key) contains the metric
            if metric in k and "Profile_length_for_FWHM" not in k:
                final_kv_pair = kv
                break

    if final_kv_pair is None and final_table is None:
        return None
    if final_kv_pair is not None:
        # Return the found key-value pair
        # kv_item = list[list[key, value]]
        return pd.DataFrame(final_kv_pair, columns=["Key", "Value"])
    else:
        # Return the OMERO table
        # FIXME THIS part has not been tested
        return omero_table_to_dataframe(conn, final_table)
        # FIXME this is the previous version
        # final_table = omero_table_to_dict(final_table)
        # # Convert to dict for pandas
        # final_table = {k: [v] for k, v in final_table.items()}
        # return pd.DataFrame.from_dict(final_table)


def get_channel_names(conn: BlitzGateway, datatype: str, id: int):
    """
    Get the channel names stored for an image on OMERO.

    :param conn: BlitzGateway
    :param datatype: str, if not "Image" returns empty list
    :param id: int, Image ID

    :return: list of channel names (empty if datatype != Image)
    """
    if datatype != "Image":
        return []
    # Get image object
    img = conn.getObject(datatype, id)
    # Return list of channel names
    return img.getChannelLabels()


def get_voxel_size(conn: BlitzGateway, datatype: str, id: int):
    """
    Get the voxel sizes stored for an image on OMERO.

    :param conn: BlitzGateway
    :param datatype: str, if not "Image" returns empty list
    :param id: int, Image ID

    :return: list of XYZ voxel size (empty if datatype != Image)
    """
    if datatype != "Image":
        return []
    # Get image object
    img = conn.getObject(datatype, id)
    # Get pixel information
    p = img.getPrimaryPixels()
    # Get the XYZ values
    v = [
        p.getPhysicalSizeX().getValue(),
        p.getPhysicalSizeY().getValue(),
        p.getPhysicalSizeZ().getValue(),
    ]
    return v


def get_omero_ring_rois(
    conn: BlitzGateway,
    image_id: int,
    roi_categories: Optional[list[str]] = None,
) -> tuple[dict, dict]:
    """
    Get the OMERO field distortion ROIs for a specified image id.

    see also: https://omero.readthedocs.io/en/v5.6.10/developers/Python.html#rois

    :param conn: BlitzGateway
    :param id: int, Image ID
    :param tags: list[str], of roi categroies/names, must be a length of 2

    :return: (dict, dict) for detected_rois and ideal_locations
        each dict has keys "001" (roi number)
        and value centroid (X, Y) in pixel units
    """
    image = conn.getObject("image", image_id)
    # print("image:", image, image.getId(), type(image))
    if image is None:
        raise RuntimeError(f"ID <{image_id} does not seem to be an Image ID.")

    # Get the ROI wrapper from the image
    if roi_categories is None:
        roi_categories = ["detected rings", "ideal locations"]
    # Dict of detected rois {nr: (centroid)}
    detected_rois = {}
    ideal_rois = {}
    for roi in image.getROIs():
        # print("roiid:", roi.getId())
        # print("n roi shapes:", len(roi.copyShapes()))

        # Get the group name (?) e.g. "detected rings"
        # print(roi.getName())
        # Only get ROI if they are in the correct category
        roi_category = roi.getName()
        if roi_category in roi_categories:
            # With copyShapes, the details of the ROIs can be retrieved
            for s in roi.copyShapes():
                # Get the name shown / comment shown in OMERO e.g. "detected rings_ROI-1"
                roi_name = s.getTextValue().getValue()
                # print(roi_name)
                # Get the ROI number as string
                try:
                    n = int(roi_name.split("ROI-")[1])
                    # Convert to e.g. "001"
                    n = str(n).zfill(3)
                except ValueError as err:
                    raise ValueError(
                        f"Could not parse ROI number for ROI name: {roi_name}."
                    ) from err
                # Get centroid as tuple
                centroid = (s.getX().getValue(), s.getY().getValue())
                # Add to the dicts
                if roi_category == roi_categories[0]:
                    detected_rois[n] = centroid
                else:
                    ideal_rois[n] = centroid
    # Sanity test
    if len(detected_rois) != len(ideal_rois):
        raise RuntimeError(
            f"The number of detected spots ({len(detected_rois)}) is not the same as the the ideal spots ({len(ideal_rois)})."
        )
    if len(detected_rois) == 0:
        raise RuntimeError(
            "No rois ('detected rings' or 'ideal location') found in image."
        )
    return detected_rois, ideal_rois


def get_field_distortion(
    detected: dict[str, tuple[float, float]],
    ideal: dict[str, tuple[float, float]],
) -> dict[str, float]:
    """
    Calculate the distance between detected points and ideal location.

    :param detected: dict, with str point number and tuple XY coordinates
    :param ideal: dict, with str point number and tuple XY coordinates

    :return: dict, with str point number and distance
    """
    # Sanity check
    if len(detected) != len(ideal):
        raise ValueError(
            "Cannot calculate field distortion when number of detected != ideal points."
        )

    dist = {}
    for k in detected.keys():
        dist[k] = point_2d_point_distance(detected.get(k), ideal.get(k))
    return dist


def get_omero_table(
    conn: BlitzGateway, image_id: int, name_part: str
) -> pd.DataFrame:
    """
    Get an OMERO table as dataframe.

    INFO: image has 2 tables (files)
    - "Field_distortion" with what looks like calibrated distances per channel (but how is the final ring position calculated?)
    - "Field_uniformity" with intensities per channel e.g. "ch0"

    :param conn: BlitzGateway
    :param image_id: int, Image ID
    :param name_part: str, substring of the table name, e.g.:
        - "Field_distortion" for distortion table
        - "Field_uniformity" for uniformity (intensity) table
        -> Attention: if multiple tables contain the substring, only the first one will be returned.

    :return: pd.DataFrame (Image, and Image_ID columns removed)
    """
    image = conn.getObject("image", image_id)
    if image is None:
        raise RuntimeError(f"ID <{image_id} does not seem to be an Image ID.")

    # Find the OMERO tables (# FIXME: returns the first table that matches the substring)
    for ann in image.listAnnotations():
        # Check for tables
        if isinstance(ann, FileAnnotationWrapper):
            if name_part in ann.getFileName():
                return omero_table_to_dataframe(conn, ann)

    # Raise error if file not found
    raise FileExistsError(
        f"No '*{name_part}*' table could be found for image {image_id}: {image.getName()}"
    )


def omero_table_to_dataframe(
    conn: BlitzGateway, ann: Union[FileAnnotationWrapper, Any]
) -> pd.DataFrame:
    """
    Convert the OMERO table object to a dataframe.

    Additionally:
        - will convert the type of Ring_ID to 1-based integer (instead of float), if available.
        - removes columns Image, Image_ID, if available.

    See also: https://omero.readthedocs.io/en/stable/developers/Tables.html

    :param: conn, BlitzGateway
    :param ann: FileAnnotationWrapper or already opened OMERO table object

    :return: pd.DataFrame
    """
    if isinstance(ann, FileAnnotationWrapper):
        res = conn.c.sf.sharedResources()
        try:
            table = res.openTable(ann.getFile()._obj)
        except Exception as err:
            raise RuntimeError(
                f"Could not open table: {ann.getFileName()}. Error: {err}"
            ) from err
    else:
        table = ann
    # Parse the table
    headers = table.getHeaders()
    n_rows = table.getNumberOfRows()
    data = table.read((range(len(headers))), start=0, stop=n_rows)
    # data is a collection of column objects (with name, values, etc.)

    # Convert to dataframe
    df = {col.name: col.values for col in data.columns}
    df = pd.DataFrame().from_dict(df)

    # Drop Image and Image_ID columns
    cols = []
    if "Image" in df.columns:
        cols.append("Image")
    if "Image_ID" in df.columns:
        cols.append("Image_ID")
    df = df.drop(columns=cols)

    # Convert the "Ring_ID" column to int
    if "Ring_ID" in df.columns:
        df["Ring_ID"] = df["Ring_ID"].astype(int).add(1)
    return df


def get_field_of_ring_grid_size(
    coords: dict[str, tuple[float, float]],
) -> tuple[int, int]:
    """
    Calculate the number of detected rings in X and Y.

    With the argolight slide, the middle ring is missing (there's a cross).

    :param coords:, dict of str point number and XY coordinates

    :return: tuple, ring count in x and y
    """
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


if __name__ == "__main__":
    # """
    # from sara (dataset with second last image containing a table) -> PSF
    # Dataset ID: 79006
    #     Image ID: 2861227

    # from myself image containing key-value pairs -> PSF
    # Dataset ID: 78303
    #     Image ID: 2832822
    # """

    # Test for get_images_for_metric (on metrology dataset (from myself)) -> PSF
    # ds_id = 81080
    # #ds_id = 78303
    # get_images_for_metric(ds_id, "PSF")

    # Uniformity / distortion
    # sara's datasetID: 79006
    # with imageID: 3021627
    pass
