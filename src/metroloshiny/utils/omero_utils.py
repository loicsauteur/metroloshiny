"""Utils for getting OMERO data."""

from typing import Optional

from omero.gateway import (
    BlitzGateway,
    FileAnnotationWrapper,
    MapAnnotationWrapper,
)

from metroloshiny.utils.read_file import get_private_data


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
        the_thing = find_metrics(
            conn=conn,
            datatype=datatype,
            kv_paris=kv,
            tables=tables,
            metric="FWHM",
        )
        return the_thing

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


def find_metrics(
    conn: BlitzGateway,
    datatype: str,
    kv_paris: list,
    tables: list,
    metric: str,
):
    """
    Check if the searched metric is in any kv_pair or OMERO.table.

    :param conn: BlitzGateway,
    :param datatype: str OMERO object datatype
    :param kv_paris: list of (loaded) OMERO key value pairs
                     (list of key-value tuples)
    :param tables: list of OMERO.table annotations
    :param metric: str Metric to find.

    :return: Either the kev-value pairs list[tuple], or OMERO.table Annotation
    """
    # Check key-value pairs for metric of interest
    kv_item = None
    for kv in kv_paris:
        # loop over the tuples of length 2,
        for k, _v in kv:
            # Check if the first item (key) contains the metric
            if metric in k:
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
        print("Found in kv and tables, returning table")
        return table_item
    if kv_item is not None:
        print("Found only in kv")
        return kv_item
    if table_item is not None:
        print("Found only in table")
        return table_item
    if kv_item is None and table_item is None:
        raise RuntimeError(
            f"Could not find <{metric}> in key-value "
            f"pairs or table of the {datatype}."
        )


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
        raise KeyError(f"<{datatype}> not a valid OMERO datatype")
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


def omero_key_value_to_dict(conn: BlitzGateway):
    """
    Test function.

    Deprectaed!
    """
    image = conn.getObject("Image", 2832822)
    kv_paris = []
    # Find key value paris in the annotations
    for ann in image.listAnnotations():
        if isinstance(ann, MapAnnotationWrapper):
            kv_paris.append(ann)
            # for k, v in ann.getValue():  # list of (key, value) tuples
            #     print(f"{k}: {v}")
            # print("***")
            # print(type(ann.getValue()))
            # print(ann.getValue())
        # if ann.OMERO_TYPE == "MapAnnotationI":
        #     kv_pairs = ann.getValue()  # list of (key, value) tuples
        #     for k, v in kv_pairs:
        #         print(k, ":", v)
        else:
            print("---Found omero type:", ann.OMERO_TYPE)

    if len(kv_paris) == 0:
        print("No key-value pairs found for ...")  # FIXME
    elif len(kv_paris) > 1:
        raise NotImplementedError(
            f"Multiple key-value pairs found for image... -> "
            f"{len(kv_paris)} key-value pair objects!"
        )  # FIXME
    # Convert key-value to a dict
    dict_out = {}
    for k, v in kv_paris[0].getValue():
        if k in dict_out.keys():
            raise RuntimeError(f"Key not unique in key-value pairs: {k}")
        dict_out[k] = v
    return dict_out


def find_omero_table(conn: BlitzGateway):
    """
    Test function.

    Deprectaed!
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
    return omero_table_to_dict(tables[0], conn=conn)


def omero_table_to_dict(
    ann: FileAnnotationWrapper, conn: BlitzGateway
) -> dict:
    """
    Get an OMERO.table as a dictionary.

    Deprectaed!
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


def render_dict(d: dict):
    """
    Print a dictionary for CLI viewing.

    Deprectaed!
    """
    if d is None:
        print("--not a dictionary--")
        return
    print("{")
    for k, v in d.items():
        print("  ", k, "=", v)
    print("}")


if __name__ == "__main__":
    connect_test()
    """
    from sara (dataset with second last image containing a table)
    Dataset ID: 79006
        Image ID: 2861227

    from myself image containing key-value pairs
    Dataset ID: 78303
        Image ID: 2832822
    """
