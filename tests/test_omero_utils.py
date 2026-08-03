"""
Tests for OMERO utils.

Most tests will not run in pytest,
as they require login credentials and connection to an OMERO instance.
"""

import pytest
from omero.gateway import BlitzGateway

import metroloshiny.utils.omero_utils as ou
from metroloshiny.utils.common_utils import (
    set_local_file,
)


def test_get_cred():
    """Test get_cred function with example private_data.csv."""
    # Test on example file
    name, pwd, host, port = ou.get_cred(
        path_private_data="./example_files/private_data_example.csv"
    )
    assert name == "user"
    assert pwd == "password"
    assert host == "omero.idr.com"
    assert isinstance(port, int)
    assert port == 4064

    # Test on file that does not exisist
    with pytest.raises(FileExistsError, match=r"File does not *"):
        ou.get_cred(path_private_data="example_files/example.csv")

    # Test on wrong file
    with pytest.raises(ValueError, match=r"Wrong private_data.csv file*"):
        ou.get_cred(
            path_private_data="./example_files/example_thorlabs_powermeter_linearity-DAPI.csv"
        )


def test_get_images_in_dataset_by_tag():
    """
    Test get_images_in_dataset_by_tag function.

    Does not run in pytest.

    Uniformity / distortion
    sara's datasetID: 79006
    with imageID: 3021627
    """
    # Skip pytest if on local file
    if set_local_file():
        return

    ds_id = 79006
    tag_uni = "field_uniformity"
    tag_dist = "field_distortion"

    # Run test with try for OMERO connection
    try:
        usr, pwd, host, port = ou.get_cred()
        conn = BlitzGateway(
            username=usr, passwd=pwd, host=host, port=port, secure=True
        )
        conn.connect()

        # Perform tests         ######################
        # Test wrong dataset ID
        with pytest.raises(
            RuntimeError, match=r"<* does not seem to be a dataset ID."
        ):
            ou.get_images_in_dataset_by_tag(conn, 1, [tag_uni])
        # Test dataset without any images
        with pytest.raises(
            RuntimeError, match=r"There are no images for datase*"
        ):
            ou.get_images_in_dataset_by_tag(conn, 82076, [tag_uni])

        # Check tag search
        tags = [tag_uni]
        imgs = ou.get_images_in_dataset_by_tag(conn, ds_id, tags)
        msg = f"Expected 5 images in dataset {ds_id} for {tags} but found {len(imgs)}; IDs={imgs.keys()}. Maybe something changed on OMERO?"
        assert len(imgs) == 5, msg

        tags = [tag_dist]
        imgs = ou.get_images_in_dataset_by_tag(conn, ds_id, tags)
        msg = f"Expected 5 images in dataset {ds_id} for {tags} but found {len(imgs)}; IDs={imgs.keys()}. Maybe something changed on OMERO?"
        assert len(imgs) == 5, msg

        tags = [tag_uni, tag_dist]
        imgs = ou.get_images_in_dataset_by_tag(conn, ds_id, tags)
        msg = f"Expected 5 images in dataset {ds_id} for {tags} but found {len(imgs)}; IDs={imgs.keys()}. Maybe something changed on OMERO?"
        assert len(imgs) == 1, msg

        # Check non-existing tag
        imgs = ou.get_images_in_dataset_by_tag(conn, ds_id, ["1random69Text"])
        assert len(imgs) == 0

    finally:
        conn.c.closeSession()


def test_get_omero_ring_rois():
    """
    Test field uniformity and distortion function.

    Tests:
    - get_omero_ring_rois
    - get_field_distortion
    - get_omero_field_uniformity_table

    TODO: maybe check several ROI related functions.

    Does not run in pytest.

    Uniformity / distortion
    sara's datasetID: 79006
    with imageID: 3021627
    """
    # Skip pytest if on local file
    if set_local_file():
        return

    ds_id = 79006
    tags = ["field_uniformity", "field_distortion"]

    try:
        usr, pwd, host, port = ou.get_cred()
        conn = BlitzGateway(
            username=usr, passwd=pwd, host=host, port=port, secure=True
        )
        conn.connect()

        # Perform tests         ##############################################
        # Get image(s) with should contain ROIs
        imgs = ou.get_images_in_dataset_by_tag(conn, ds_id, tags)
        image_id = next(iter(imgs))  # Get the first image ID in the dict
        # Get the detected and ideal rois from the image
        detected, ideal = ou.get_omero_ring_rois(conn, image_id)

        # Check that the names (keys) are equal for both: ideal and detected
        for i in detected.keys():
            assert i in ideal.keys()

        # Calculate the number of X/Y rings
        x_rings, y_rings = ou.get_field_of_ring_grid_size(detected)
        n_rings = x_rings * y_rings
        # assert n_detected rings == x * y (optional -1, since center ring may be missing)
        assert len(detected) == n_rings - 1 or len(detected) == n_rings

        # Check field distortion        ------------------------
        distortion = ou.get_field_distortion(detected, ideal)
        assert len(distortion) == len(detected)
        # for k, v in distortion.items():
        #     print(k, v)

        # Additional dummy check
        dist = ou.get_field_distortion(detected, detected)
        assert sum(dist.values()) == 0

        # Get the field uniformity and distortion tables        ##############
        dist_df = ou.get_omero_table(conn, image_id, "Field_distortion")
        unif_df = ou.get_omero_table(conn, image_id, "Field_uniformity")
        assert len(dist_df) == len(unif_df)  # == 168

        # Test non-existing table name
        name = "1randomName"
        with pytest.raises(
            FileExistsError,
            match=rf"No '\*{name}\*' table could be found for image *",
        ):
            ou.get_omero_table(conn, image_id, name)

        # TODO have omero_utils function to get the distance between points - DONE
        #   Can i also get a vector, that could be used for visualisation?
        #   Can I calculate a heat map from the positions? -> X/Y tiles
        #   # what to do with center (average surroundings?)

    finally:
        conn.c.closeSession()


if __name__ == "__main__":
    test_get_omero_ring_rois()
