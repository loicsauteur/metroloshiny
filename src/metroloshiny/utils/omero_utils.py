"""Utils for getting OMERO data."""

from typing import Any, Callable, Optional

import pandas as pd
from omero.gateway import (
    BlitzGateway,
    FileAnnotationWrapper,
    MapAnnotationWrapper,
)

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

        # print("id with metric:")
        # for k, v in id_name_dict.items():
        #     print(k, v)

        # print("id without metrics:")
        # count = 0
        # for k in image_ids.keys():
        #     if k not in id_name_dict.keys():
        #         count += 1
        #         print(k)

        # print("total images in dataset", len(image_ids.keys()))
        # print("total images with metric", len(id_name_dict.keys()))
        # print("images without metric", count)
    finally:
        conn.c.closeSession()
    return id_name_dict, id_df_dict


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


def omero_operation(
    operation: Optional[Callable[[str, int, str], Any]],
    omero_type: str,
    omero_id: int,
    metric_id: str,
    username: Optional[str] = None,
    passwd: Optional[str] = None,
    host: Optional[str] = None,
    port: Optional[int] = None,
    path_private_data: Optional[str] = None,
) -> tuple[Optional[dict], list, list]:
    """
    Get data from OMERO.

    :param operation: callable function that takes 3 arguments:
                str = datatype, int = id, str = additional info
    :param omero_type: str for Dataset or Image
    :param omero_id: int OMERO ID
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

    :return: tuple of
        - dict with data, with keys (containing the metric string),
          or None if no matches were found.
        - list of channel names
        - list of XYZ voxels
    """
    # Get the connection details from file
    username, passwd, host, port = get_cred(
        path_private_data, username, passwd, host, port
    )
    data_dict = None
    channel_names = None
    voxel_size = None

    # Connect to OMERO
    try:
        conn = BlitzGateway(
            username=username, passwd=passwd, host=host, port=port, secure=True
        )
        conn.connect()
        # Perform operation on OMERO
        # Get any key-value or OMERO.tables for the OMERO object of interest
        kv_pairs, tables = get_tables_and_kv_paris(
            conn=conn, datatype=omero_type, id=omero_id
        )
        # Get the kv_pari or OMERO.table containing the metric of interest
        data_dict = find_metrics(
            conn=conn,
            datatype=omero_type,
            kv_paris=kv_pairs,
            tables=tables,
            metric=metric_id,
        )
        # Get the image channel name list
        channel_names = get_channel_names(
            conn=conn, datatype=omero_type, id=omero_id
        )
        # Get the image voxel sizes
        voxel_size = get_voxel_size(
            conn=conn, datatype=omero_type, id=omero_id
        )

    finally:
        conn.c.closeSession()
    # # Process the data
    # if data_dict is None:
    #     return None, channel_names, voxel_size
    return data_dict, channel_names, voxel_size


def connect_test(
    username: Optional[str] = None,
    passwd: Optional[str] = None,
    host: Optional[str] = None,
    port: Optional[int] = None,
    path_private_data: Optional[str] = None,
):
    """
    Test function.

    :param username: str optional user name, if None,
                     fetches from private_data.csv
    """
    # Get the connection details from file
    username, passwd, host, port = get_cred(
        path_private_data, username, passwd, host, port
    )
    # Connect to OMERO
    try:
        conn = BlitzGateway(
            username=username, passwd=passwd, host=host, port=port, secure=True
        )
        conn.connect()
        print("Connected")
        # TODO other function here
        datatype = "Dataset"
        kv, tables = get_tables_and_kv_paris(
            conn, datatype=datatype, id=79006
        )  # id=2861226)
        # the_thing = find_metrics(
        find_metrics(
            conn=conn,
            datatype=datatype,
            kv_paris=kv,
            tables=tables,
            metric="FWHM",
        )
        # return the_thing

    finally:
        conn.c.closeSession()
        print("Disconnected")


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


def omero_key_value_to_dict(kv_pair: list[list]) -> dict:
    """
    Convert a OMERO key-value pair list to a dictionary.

    Throws a RuntimeError if keys are not unique.
    :param kv_pair: list OMERO key-value pair

    :return: dict
    """
    dict_out = {}
    for k, v in kv_pair:
        if k in dict_out.keys():
            raise RuntimeError(f"Key not unique in key-value pairs: {k}")
        dict_out[k] = v
    return dict_out


def omero_table_to_dict(table) -> dict:
    """
    Already loaded OMERO.table to dict.

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


def omero_table_to_dict_old(
    ann: FileAnnotationWrapper, conn: BlitzGateway
) -> dict:
    """
    Get an OMERO.table as a dictionary.

    Throws a RuntimeError if there are non-unique headers.
    :param ann: FileAnnotationWrapper
    :param conn: BlitzGatewaay

    :return: dict
    """
    res = conn.c.sf.sharedResources()
    try:
        table = res.openTable(ann.getFile()._obj)
    except Exception as err:
        raise RuntimeError(
            f"Could not open table. "
            f"Input type was {ann.getFile().getMimetype()}"
        ) from err
    return omero_table_to_dict(table)


def find_metrics(
    conn: BlitzGateway,
    datatype: str,
    kv_paris: list,
    tables: list,
    metric: str,
) -> dict:
    """
    Check if the searched metric is in any kv_pair or OMERO.table.

    :param conn: BlitzGateway,
    :param datatype: str OMERO object datatype
    :param kv_paris: list of (loaded) OMERO key value pairs
        (list of key-value tuples)
    :param tables: list of OMERO.table annotations
    :param metric: str Metric to find.

    :raises RuntimeError: if the metric is not found in Omero.tables
        or key-value pairs.

    :return: dict
    """
    # Check key-value pairs for metric of interest
    kv_item = None
    for kv in kv_paris:
        # loop over the tuples of length 2,
        for k, _v in kv:
            # Check if the first item (key) contains the metric
            if metric in k and "Profile_length_for_FWHM" not in k:
                kv_item = kv
                break

    # Check tables for the metric of interest
    res = conn.c.sf.sharedResources()
    table_item = None
    for ann in tables:
        # If Image, the metric should be found in the annotation name.
        if datatype == "Image":
            table_name = ann.getFile().getName()
            if table_name == metric:
                table_item = ann
                break

        # If Dataset, the metric will be in some column name
        else:
            t = res.openTable(ann.getFile()._obj)
            for col in t.getHeaders():
                if metric in col.name:
                    table_item = ann
                    break
    # If found in both, return the table
    if kv_item is not None and table_item is not None:
        return omero_table_to_dict_old(table_item, conn=conn)
    if kv_item is not None:
        return omero_key_value_to_dict(kv_item)
    if table_item is not None:
        return omero_table_to_dict_old(table_item, conn=conn)
    if kv_item is None and table_item is None:
        raise RuntimeError(
            f"Could not find <{metric}> in key-value "
            f"pairs or table of the {datatype}."
        )


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
        # kv_item = list[list[key, value]]
        return pd.DataFrame(final_kv_pair, columns=["Key", "Value"])
    else:
        # FIXME definitively should check how this looks. Probably better to return a table directly instead of converting to a dict...!
        final_table = omero_table_to_dict(final_table)
        # Convert to dict for pandas
        final_table = {k: [v] for k, v in final_table.items()}
        return pd.DataFrame.from_dict(final_table)


def get_tables_and_kv_paris(
    conn: BlitzGateway, datatype: str, id: int
) -> tuple:
    """
    Get all OMERO.tables and key-value pairs from an OMERO object.

    (Tables not loaded yet. Key-value paris already loaded.)

    :param conn: BlitzGateway
    :param datatype: str OMERO datatype, i.e. Image, Dataset, Project
    :param id: int OMERO object id

    :return: tuple (list[key-value pairs], list[annotation of OMERO.table])
    """
    if datatype not in ["Dataset", "Project", "Image"]:
        raise RuntimeError(f"<{datatype}> not a valid OMERO datatype")
    # Get the OMERO object
    item = conn.getObject(datatype, id)
    if item is None:
        raise RuntimeError(
            f"ID <{id}> does not seem to be of type <{datatype}>."
        )
    # Initialise results
    kv_pairs = []
    tables = []
    # Loop over all annotation objects
    res = conn.c.sf.sharedResources()
    for ann in item.listAnnotations():
        # Check for tables
        if isinstance(ann, FileAnnotationWrapper):
            try:
                # if it can open a table it is one.
                res.openTable(ann.getFile()._obj)
                tables.append(ann)
            except Exception:
                # Not a table - skip
                pass
        elif isinstance(ann, MapAnnotationWrapper):
            kv_pairs.append(ann.getValue())

    if len(kv_pairs) == 0 and len(tables) == 0:
        raise RuntimeError(
            f"No key-value pairs or OMERO.tables found for {datatype} {id}"
        )
    return kv_pairs, tables


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


def find_omero_table(conn: BlitzGateway):
    """
    Test function.

    Deprecated!
    """
    image = conn.getObject("Image", 2861227)
    # image = conn.getObject("Dataset", 79006)
    tables = []  # object may contain multiple tables
    res = conn.c.sf.sharedResources()

    # Loop over object annotations
    for ann in image.listAnnotations():
        if isinstance(ann, FileAnnotationWrapper):
            # print("-------------:", ann.getFile().getMimetype())
            #           should give OMERO.tables
            # print("-------------:", ann.getNs())
            print("-------------:", ann.getFile().getName())
            # print("-------------:", ann.getDescription())
            # print("-------------:", ann.getFile().getMimetype())

            try:
                # here how to open the table
                res.openTable(ann.getFile()._obj)
                tables.append(ann)
                # print(">>>>>>>>: could open table!")
            except Exception:
                pass
                # print(">>>>>>>>: could not open table")
                # print(e)

    print("Found ", len(tables), "tables.")

    if len(tables) == 0:
        print("no tables found")
        return None
    if len(tables) > 1:
        raise NotImplementedError(
            f"OMERO object contains multiple OMERO.tables -> "
            f"{len(tables)} tables!"
        )
    return omero_table_to_dict_old(tables[0], conn=conn)


def render_dict(d: dict):
    """
    Print a dictionary for CLI viewing.

    Deprecated!
    """
    if d is None:
        print("--not a dictionary--")
        return
    print("{")
    for k, v in d.items():
        print("  ", k, "=", v)
    print("}")


if __name__ == "__main__":
    # out = omero_operation(
    #     operation=None,
    #     omero_type="Image",
    #     omero_id=2832822,
    #     metric_id="FWHM",
    # )
    # render_dict(out)

    # """
    # from sara (dataset with second last image containing a table)
    # Dataset ID: 79006
    #     Image ID: 2861227

    # from myself image containing key-value pairs
    # Dataset ID: 78303
    #     Image ID: 2832822
    # """

    # Test for get_images_for_metric (on metrology dataset (from myself))
    # ds_id = 81080
    # #ds_id = 78303
    # get_images_for_metric(ds_id, "PSF")
    pass
