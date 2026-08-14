"""
Tests for OMERO utils.

Most tests will not run in pytest,
as they require login credentials and connection to an OMERO instance.
"""

import pytest
from omero.gateway import BlitzGateway

import metroloshiny.utils.omero_utils as ou


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


@pytest.mark.manual
def test_get_images_in_dataset_by_tag():
    """
    Test get_images_in_dataset_by_tag function.

    Does only run in "pytest -m manual"

    Uniformity / distortion
    Metrology test dataset: 82171
    with imageID: 3454869
    """
    ds_id = 82171
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


@pytest.mark.manual
def test_get_omero_ring_rois():
    """
    Test field uniformity and distortion function.

    Tests:
    - get_omero_ring_rois
    - get_field_distortion
    - get_omero_field_uniformity_table

    TODO: maybe check several ROI related functions.

    Does only run in "pytest -m manual"

    Uniformity / distortion
    Metrology test dataset: 82171
    with imageID: 3454869
    """
    ds_id = 82171
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

        # Calculate the number of X/Y rings FIXME deprecated!
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


@pytest.mark.manual
def test_get_dates():
    """
    Test the get_dates function.

    Does only run in "pytest -m manual"

    ImageID with acquisition date: 3454869
        acquisition date =  2026-02-26 08:55:41
        import date =       2026-08-05 08:37:27
    ImageID w/o  acquisition date: 3454870
        import date =       2026-08-05 08:37:43
    """
    try:
        usr, pwd, host, port = ou.get_cred()
        conn = BlitzGateway(
            username=usr, passwd=pwd, host=host, port=port, secure=True
        )
        conn.connect()

        # Object with both dates
        image_id = 3454869
        d1, d2 = ou.get_dates(conn, image_id)
        assert d1 == "20260226"
        assert d2 == "20260805"

        # Object with only import date
        image_id = 3454870
        d1, d2 = ou.get_dates(conn, image_id)
        assert d1 is None
        assert d2 == "20260805"

    finally:
        conn.c.closeSession()


@pytest.mark.manual
def test_get_voxel_and_channel_names():
    """
    Test the get_dates function.

    Does only run in "pytest -m manual"

    Leica ImageID: 3454869
    Nikon ImageID: 3454870
    """
    # Leica Image
    image_id = 3454869
    voxels, ch_names = ou.get_image_voxelsize_channel_names(image_id=image_id)
    assert round(voxels[0], 2) == 0.21
    assert round(voxels[1], 2) == 0.21
    assert round(voxels[2], 2) == 1
    assert ch_names == ["0", "1", "2", "3"]

    # Nikon image
    image_id = 3454870
    voxels, ch_names = ou.get_image_voxelsize_channel_names(image_id=image_id)
    assert round(voxels[0], 2) == 0.06
    assert round(voxels[1], 2) == 0.06
    assert round(voxels[2], 2) == 0.17
    assert ch_names == ["DAPI", "GFP", "Cy3", "Cy5"]

    # A non-microscope image
    image_id = 3454874
    with pytest.raises(
        RuntimeError,
        match=f"The image <{image_id}> is not calibrated or not a microscopy image.",
    ):
        ou.get_image_voxelsize_channel_names(image_id=image_id)


@pytest.mark.manual
def test_getting_metric_functions():
    """
    Test the functions related to getting metric data.

    Does only run in "pytest -m manual"

    TODO would be nice to have parameterized functions

    Uniformity/distortion ImageID: 3454869
        Should not return any DF
    PSF ImageID: 3454870
        Should return DF with Key, Value columns

    """
    try:
        usr, pwd, host, port = ou.get_cred()
        conn = BlitzGateway(
            username=usr, passwd=pwd, host=host, port=port, secure=True
        )
        conn.connect()

        # Testing get_metric_data function          --------------------------
        # This function should be deprecated (FIXME)
        # PSF image
        image_id = 3454870
        df = ou.get_metric_data(conn, image_id=image_id, metric="FWHM")
        assert df is not None
        assert "Key" in df.columns

        # Uniformity/Distortion image
        image_id = 3454869
        df = ou.get_metric_data(conn, image_id=image_id, metric="FWHM")
        assert df is not None

        # Testing get_fwhm_metric_data              --------------------------
        # PSF image
        image_id = 3454870
        df = ou.get_fwhm_metric_data(conn, image_id, "FWHM")
        assert df is not None
        assert "Key" in df.columns
        assert "Value" in df.columns

        # Uniformity/Distortion image
        image_id = 3454869
        df = ou.get_fwhm_metric_data(conn, image_id, "FWHM")
        assert df is None

    finally:
        conn.c.closeSession()


if __name__ == "__main__":
    # TODO would be nice to have parameterized functions
    # TODO python file i could run manually to check all functions that do not run in pytest?!

    # Uniformity / distortion
    #     Metrology test dataset: 82171
    #     with imageID: 3454869
    # PSF
    #     Metrology test dataset: 82170
    #     with imageID: 3454870

    # List of all the functions
    # test_get_cred()
    # test_get_images_in_dataset_by_tag()
    # test_get_omero_ring_rois()
    # test_get_dates()
    # test_get_voxel_and_channel_names()
    # test_getting_metric_functions()
    pass
