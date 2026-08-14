"""Test PSFData object."""

import pandas as pd

from metroloshiny.data_objects.psf_data import PSFData

omero_4ch_multi_roi_full_kv = {
    "C1_FWHM_Axial_X_ROI_0277-0168-0137": 0,
    "C1_FWHM_Axial_Y_ROI_0277-0168-0137": "762",
    "C1_FWHM_Axial_avg_ROI_0277-0168-0137": 381,
    "C1_FWHM_Z_ROI_0277-0168-0137": 1253,
    "C2_shift_X_ROI_0277-0168-0137": -3,
    "C2_shift_Y_ROI_0277-0168-0137": 3,
    "C2_shift_Z_ROI_0277-0168-0137": 6,
    "C2_FWHM_Axial_X_ROI_0277-0168-0137": 826,
    "C2_FWHM_Axial_Y_ROI_0277-0168-0137": 663,
    "C2_FWHM_Axial_avg_ROI_0277-0168-0137": 744,
    "C2_FWHM_Z_ROI_0277-0168-0137": 981,
    "C3_shift_X_ROI_0277-0168-0137": 1,
    "C3_shift_Y_ROI_0277-0168-0137": 1,
    "C3_shift_Z_ROI_0277-0168-0137": 3,
    "C3_FWHM_Axial_X_ROI_0277-0168-0137": 905,
    "C3_FWHM_Axial_Y_ROI_0277-0168-0137": 985,
    "C3_FWHM_Axial_avg_ROI_0277-0168-0137": 945,
    "C3_FWHM_Z_ROI_0277-0168-0137": 1012,
    "C4_shift_X_ROI_0277-0168-0137": 4,
    "C4_shift_Y_ROI_0277-0168-0137": -2,
    "C4_shift_Z_ROI_0277-0168-0137": 4,
    "C4_FWHM_Axial_X_ROI_0277-0168-0137": 919,
    "C4_FWHM_Axial_Y_ROI_0277-0168-0137": 988,
    "C4_FWHM_Axial_avg_ROI_0277-0168-0137": 954,
    "C4_FWHM_Z_ROI_0277-0168-0137": 1141,
    "C1_FWHM_Axial_X_ROI_0277-0209-0323": 786,
    "C1_FWHM_Axial_Y_ROI_0277-0209-0323": 746,
    "C1_FWHM_Axial_avg_ROI_0277-0209-0323": 766,
    "C1_FWHM_Z_ROI_0277-0209-0323": 1167,
    "C2_shift_X_ROI_0277-0209-0323": 0,
    "C2_shift_Y_ROI_0277-0209-0323": -8,
    "C2_shift_Z_ROI_0277-0209-0323": 6,
    "C2_FWHM_Axial_X_ROI_0277-0209-0323": 521,
    "C2_FWHM_Axial_Y_ROI_0277-0209-0323": 596,
    "C2_FWHM_Axial_avg_ROI_0277-0209-0323": 558,
    "C2_FWHM_Z_ROI_0277-0209-0323": 715,
    "C3_shift_X_ROI_0277-0209-0323": -1,
    "C3_shift_Y_ROI_0277-0209-0323": -8,
    "C3_shift_Z_ROI_0277-0209-0323": 4,
    "C3_FWHM_Axial_X_ROI_0277-0209-0323": 784,
    "C3_FWHM_Axial_Y_ROI_0277-0209-0323": 822,
    "C3_FWHM_Axial_avg_ROI_0277-0209-0323": 803,
    "C3_FWHM_Z_ROI_0277-0209-0323": 1020,
    "C4_shift_X_ROI_0277-0209-0323": -6,
    "C4_shift_Y_ROI_0277-0209-0323": -10,
    "C4_shift_Z_ROI_0277-0209-0323": 5,
    "C4_FWHM_Axial_X_ROI_0277-0209-0323": 879,
    "C4_FWHM_Axial_Y_ROI_0277-0209-0323": 849,
    "C4_FWHM_Axial_avg_ROI_0277-0209-0323": 864,
    "C4_FWHM_Z_ROI_0277-0209-0323": 1107,
    "C1_FWHM_Axial_X_ROI_0277-0315-0137": 724,
    "C1_FWHM_Axial_Y_ROI_0277-0315-0137": 776,
    "C1_FWHM_Axial_avg_ROI_0277-0315-0137": 750,
    "C1_FWHM_Z_ROI_0277-0315-0137": 1287,
    "C2_shift_X_ROI_0277-0315-0137": -4,
    "C2_shift_Y_ROI_0277-0315-0137": -5,
    "C2_shift_Z_ROI_0277-0315-0137": 7,
    "C2_FWHM_Axial_X_ROI_0277-0315-0137": 606,
    "C2_FWHM_Axial_Y_ROI_0277-0315-0137": 575,
    "C2_FWHM_Axial_avg_ROI_0277-0315-0137": 590,
    "C2_FWHM_Z_ROI_0277-0315-0137": 895,
    "C3_shift_X_ROI_0277-0315-0137": -3,
    "C3_shift_Y_ROI_0277-0315-0137": -4,
    "C3_shift_Z_ROI_0277-0315-0137": 5,
    "C3_FWHM_Axial_X_ROI_0277-0315-0137": 863,
    "C3_FWHM_Axial_Y_ROI_0277-0315-0137": 905,
    "C3_FWHM_Axial_avg_ROI_0277-0315-0137": 884,
    "C3_FWHM_Z_ROI_0277-0315-0137": 1051,
    "C4_shift_X_ROI_0277-0315-0137": -6,
    "C4_shift_Y_ROI_0277-0315-0137": -1,
    "C4_shift_Z_ROI_0277-0315-0137": 7,
    "C4_FWHM_Axial_X_ROI_0277-0315-0137": 0,
    "C4_FWHM_Axial_Y_ROI_0277-0315-0137": 1104,
    "C4_FWHM_Axial_avg_ROI_0277-0315-0137": 552,
    "C4_FWHM_Z_ROI_0277-0315-0137": 1180,
    "C1_FWHM_Axial_X_ROI_0277-0354-0342": 1224,
    "C1_FWHM_Axial_Y_ROI_0277-0354-0342": 1125,
    "C1_FWHM_Axial_avg_ROI_0277-0354-0342": 1174,
    "C1_FWHM_Z_ROI_0277-0354-0342": 1331,
    "C2_shift_X_ROI_0277-0354-0342": 2,
    "C2_shift_Y_ROI_0277-0354-0342": 1,
    "C2_shift_Z_ROI_0277-0354-0342": 6,
    "C2_FWHM_Axial_X_ROI_0277-0354-0342": 0,
    "C2_FWHM_Axial_Y_ROI_0277-0354-0342": 739,
    "C2_FWHM_Axial_avg_ROI_0277-0354-0342": 369,
    "C2_FWHM_Z_ROI_0277-0354-0342": 848,
    "C3_shift_X_ROI_0277-0354-0342": 6,
    "C3_shift_Y_ROI_0277-0354-0342": -2,
    "C3_shift_Z_ROI_0277-0354-0342": 4,
    "C3_FWHM_Axial_X_ROI_0277-0354-0342": 741,
    "C3_FWHM_Axial_Y_ROI_0277-0354-0342": 794,
    "C3_FWHM_Axial_avg_ROI_0277-0354-0342": 768,
    "C3_FWHM_Z_ROI_0277-0354-0342": 999,
    "C4_shift_X_ROI_0277-0354-0342": 5,
    "C4_shift_Y_ROI_0277-0354-0342": -6,
    "C4_shift_Z_ROI_0277-0354-0342": 3,
    "C4_FWHM_Axial_X_ROI_0277-0354-0342": 895,
    "C4_FWHM_Axial_Y_ROI_0277-0354-0342": 873,
    "C4_FWHM_Axial_avg_ROI_0277-0354-0342": 884,
    "C4_FWHM_Z_ROI_0277-0354-0342": 1142,
    "AVERAGE_FWHM_X_All_ROIS_C1": 912.0,
    "AVERAGE_FWHM_Y_All_ROIS_C1": 853.0,
    "AVERAGE_FWHM_Z_All_ROIS_C1": 1260.0,
    "AVERAGE_FWHM_X_All_ROIS_C2": 651.0,
    "AVERAGE_FWHM_Y_All_ROIS_C2": 644.0,
    "AVERAGE_FWHM_Z_All_ROIS_C2": 860.0,
    "AVERAGE_FWHM_X_All_ROIS_C3": 824.0,
    "AVERAGE_FWHM_Y_All_ROIS_C3": 877.0,
    "AVERAGE_FWHM_Z_All_ROIS_C3": 1021.0,
    "AVERAGE_FWHM_X_All_ROIS_C4": 898.0,
    "AVERAGE_FWHM_Y_All_ROIS_C4": 954.0,
    "AVERAGE_FWHM_Z_All_ROIS_C4": 1143.0,
    "ACQUISITION_DATE": "2026-04-24",
    "MICROSCOPE": "maintenanceTest",
    "OBJECTIVE_MAGNIFICATION": "0x",
    "OBJECTIVE_NA": "0",
    "ACQUISITION_DATE_NUMBER": "20260424",
}

omero_2ch_multi_roi_full_kv = {
    "C1_FWHM_Axial_X_ROI_0277-0168-0137": 0,
    "C1_FWHM_Axial_Y_ROI_0277-0168-0137": 762,
    "C1_FWHM_Axial_avg_ROI_0277-0168-0137": 381,
    "C1_FWHM_Z_ROI_0277-0168-0137": 1253,
    "C2_shift_X_ROI_0277-0168-0137": -3,
    "C2_shift_Y_ROI_0277-0168-0137": 3,
    "C2_shift_Z_ROI_0277-0168-0137": 6,
    "C2_FWHM_Axial_X_ROI_0277-0168-0137": 826,
    "C2_FWHM_Axial_Y_ROI_0277-0168-0137": 663,
    "C2_FWHM_Axial_avg_ROI_0277-0168-0137": 744,
    "C2_FWHM_Z_ROI_0277-0168-0137": 981,
    "C1_FWHM_Axial_X_ROI_0277-0209-0323": 786,
    "C1_FWHM_Axial_Y_ROI_0277-0209-0323": 746,
    "C1_FWHM_Axial_avg_ROI_0277-0209-0323": 766,
    "C1_FWHM_Z_ROI_0277-0209-0323": 1167,
    "C2_shift_X_ROI_0277-0209-0323": 0,
    "C2_shift_Y_ROI_0277-0209-0323": -8,
    "C2_shift_Z_ROI_0277-0209-0323": 6,
    "C2_FWHM_Axial_X_ROI_0277-0209-0323": 521,
    "C2_FWHM_Axial_Y_ROI_0277-0209-0323": 596,
    "C2_FWHM_Axial_avg_ROI_0277-0209-0323": 558,
    "C2_FWHM_Z_ROI_0277-0209-0323": 715,
    "C1_FWHM_Axial_X_ROI_0277-0315-0137": 724,
    "C1_FWHM_Axial_Y_ROI_0277-0315-0137": 776,
    "C1_FWHM_Axial_avg_ROI_0277-0315-0137": 750,
    "C1_FWHM_Z_ROI_0277-0315-0137": 1287,
    "C2_shift_X_ROI_0277-0315-0137": -4,
    "C2_shift_Y_ROI_0277-0315-0137": -5,
    "C2_shift_Z_ROI_0277-0315-0137": 7,
    "C2_FWHM_Axial_X_ROI_0277-0315-0137": 606,
    "C2_FWHM_Axial_Y_ROI_0277-0315-0137": 575,
    "C2_FWHM_Axial_avg_ROI_0277-0315-0137": 590,
    "C2_FWHM_Z_ROI_0277-0315-0137": 895,
    "C1_FWHM_Axial_X_ROI_0277-0354-0342": 1224,
    "C1_FWHM_Axial_Y_ROI_0277-0354-0342": 1125,
    "C1_FWHM_Axial_avg_ROI_0277-0354-0342": 1174,
    "C1_FWHM_Z_ROI_0277-0354-0342": 1331,
    "C2_shift_X_ROI_0277-0354-0342": 2,
    "C2_shift_Y_ROI_0277-0354-0342": 1,
    "C2_shift_Z_ROI_0277-0354-0342": 6,
    "C2_FWHM_Axial_X_ROI_0277-0354-0342": 0,
    "C2_FWHM_Axial_Y_ROI_0277-0354-0342": 739,
    "C2_FWHM_Axial_avg_ROI_0277-0354-0342": 369,
    "C2_FWHM_Z_ROI_0277-0354-0342": 848,
    "AVERAGE_FWHM_X_All_ROIS_C1": 912.0,
    "AVERAGE_FWHM_Y_All_ROIS_C1": 853.0,
    "AVERAGE_FWHM_Z_All_ROIS_C1": 1260.0,
    "AVERAGE_FWHM_X_All_ROIS_C2": 651.0,
    "AVERAGE_FWHM_Y_All_ROIS_C2": 644.0,
    "AVERAGE_FWHM_Z_All_ROIS_C2": 860.0,
    "ACQUISITION_DATE": "2026-04-24",
    "MICROSCOPE": "maintenanceTest",
    "OBJECTIVE_MAGNIFICATION": "0x",
    "OBJECTIVE_NA": "0",
    "ACQUISITION_DATE_NUMBER": "20260424",
}

omero_2ch_multi_roi_no_avg_kv = {
    "C1_FWHM_Axial_X_ROI_0277-0168-0137": 0,
    "C1_FWHM_Axial_Y_ROI_0277-0168-0137": 762,
    "C1_FWHM_Axial_avg_ROI_0277-0168-0137": 381,
    "C1_FWHM_Z_ROI_0277-0168-0137": 1253,
    "C2_shift_X_ROI_0277-0168-0137": -3,
    "C2_shift_Y_ROI_0277-0168-0137": 3,
    "C2_shift_Z_ROI_0277-0168-0137": 6,
    "C2_FWHM_Axial_X_ROI_0277-0168-0137": 826,
    "C2_FWHM_Axial_Y_ROI_0277-0168-0137": 663,
    "C2_FWHM_Axial_avg_ROI_0277-0168-0137": 744,
    "C2_FWHM_Z_ROI_0277-0168-0137": 981,
    "C1_FWHM_Axial_X_ROI_0277-0209-0323": 786,
    "C1_FWHM_Axial_Y_ROI_0277-0209-0323": 746,
    "C1_FWHM_Axial_avg_ROI_0277-0209-0323": 766,
    "C1_FWHM_Z_ROI_0277-0209-0323": 1167,
    "C2_shift_X_ROI_0277-0209-0323": 0,
    "C2_shift_Y_ROI_0277-0209-0323": -8,
    "C2_shift_Z_ROI_0277-0209-0323": 6,
    "C2_FWHM_Axial_X_ROI_0277-0209-0323": 521,
    "C2_FWHM_Axial_Y_ROI_0277-0209-0323": 596,
    "C2_FWHM_Axial_avg_ROI_0277-0209-0323": 558,
    "C2_FWHM_Z_ROI_0277-0209-0323": 715,
    "C1_FWHM_Axial_X_ROI_0277-0315-0137": 724,
    "C1_FWHM_Axial_Y_ROI_0277-0315-0137": 776,
    "C1_FWHM_Axial_avg_ROI_0277-0315-0137": 750,
    "C1_FWHM_Z_ROI_0277-0315-0137": 1287,
    "C2_shift_X_ROI_0277-0315-0137": -4,
    "C2_shift_Y_ROI_0277-0315-0137": -5,
    "C2_shift_Z_ROI_0277-0315-0137": 7,
    "C2_FWHM_Axial_X_ROI_0277-0315-0137": 606,
    "C2_FWHM_Axial_Y_ROI_0277-0315-0137": 575,
    "C2_FWHM_Axial_avg_ROI_0277-0315-0137": 590,
    "C2_FWHM_Z_ROI_0277-0315-0137": 895,
    "C1_FWHM_Axial_X_ROI_0277-0354-0342": 1224,
    "C1_FWHM_Axial_Y_ROI_0277-0354-0342": 1125,
    "C1_FWHM_Axial_avg_ROI_0277-0354-0342": 1174,
    "C1_FWHM_Z_ROI_0277-0354-0342": 1331,
    "C2_shift_X_ROI_0277-0354-0342": 2,
    "C2_shift_Y_ROI_0277-0354-0342": 1,
    "C2_shift_Z_ROI_0277-0354-0342": 6,
    "C2_FWHM_Axial_X_ROI_0277-0354-0342": 0,
    "C2_FWHM_Axial_Y_ROI_0277-0354-0342": 739,
    "C2_FWHM_Axial_avg_ROI_0277-0354-0342": 369,
    "C2_FWHM_Z_ROI_0277-0354-0342": 848,
    "ACQUISITION_DATE": "2026-04-24",
    "MICROSCOPE": "maintenanceTest",
    "OBJECTIVE_MAGNIFICATION": "0x",
    "OBJECTIVE_NA": "0",
    "ACQUISITION_DATE_NUMBER": "20260424",
}

omero_2ch_single_roi_kv = {
    "C1_FWHM_Axial_X_ROI_0277-0168-0137": 0,
    "C1_FWHM_Axial_Y_ROI_0277-0168-0137": 762,
    "C1_FWHM_Axial_avg_ROI_0277-0168-0137": 381,
    "C1_FWHM_Z_ROI_0277-0168-0137": 1253,
    "C2_shift_X_ROI_0277-0168-0137": -3,
    "C2_shift_Y_ROI_0277-0168-0137": 3,
    "C2_shift_Z_ROI_0277-0168-0137": 6,
    "C2_FWHM_Axial_X_ROI_0277-0168-0137": 826,
    "C2_FWHM_Axial_Y_ROI_0277-0168-0137": 663,
    "C2_FWHM_Axial_avg_ROI_0277-0168-0137": 744,
    "C2_FWHM_Z_ROI_0277-0168-0137": 981,
    "ACQUISITION_DATE": "2026-04-24",
    "MICROSCOPE": "maintenanceTest",
    "OBJECTIVE_MAGNIFICATION": "0x",
    "OBJECTIVE_NA": "0",
    "ACQUISITION_DATE_NUMBER": "20260424",
}
omero_1ch_single_roi_kv = {
    "C1_FWHM_Axial_X_ROI_1018-1080": 401,
    "C1_FWHM_Axial_Y_ROI_1018-1080": 402,
    "C1_FWHM_Axial_avg_ROI_1018-1080": 401,
    "C1_FWHM_Z_ROI_1018-1080": 1412,
    "ACQUISITION_DATE": "2026-02-13",
    "MICROSCOPE": "maintenanceTest",
    "OBJECTIVE_MAGNIFICATION": "0x",
    "OBJECTIVE_NA": "0",
    "ACQUISITION_DATE_NUMBER": "20260213",
}


def test_psfdata():
    """Test PSFData object creation."""
    ch4_full = PSFData(omero_4ch_multi_roi_full_kv)
    ch2_full = PSFData(omero_2ch_multi_roi_full_kv)
    ch2_no_avg = PSFData(omero_2ch_multi_roi_no_avg_kv)
    ch2_single = PSFData(omero_2ch_single_roi_kv)
    ch1_single = PSFData(omero_1ch_single_roi_kv)

    # Check correct number of channesl
    assert ch4_full.n_channels == 4
    assert ch2_full.n_channels == 2
    assert ch2_no_avg.n_channels == 2
    assert ch2_single.n_channels == 2
    assert ch1_single.n_channels == 1

    # Make sure that final data dict have single float values
    val = ch4_full.fwhm_data["C2"].get("FWHM-Y")
    assert isinstance(val, float), f"Shout be float but was {type(val)}"
    val = ch2_full.fwhm_data["C2"].get("FWHM-Y")
    assert isinstance(val, float), f"Shout be float but was {type(val)}"
    val = ch2_no_avg.fwhm_data["C2"].get("FWHM-Y")
    assert isinstance(val, float), f"Shout be float but was {type(val)}"
    val = ch2_single.fwhm_data["C2"].get("FWHM-Y")
    assert isinstance(val, float), f"Shout be float but was {type(val)}"

    # Check shift data
    assert len(ch4_full.get_shift_data()) == ch4_full.n_channels
    assert len(ch2_full.get_shift_data()) == ch2_full.n_channels
    assert len(ch2_no_avg.get_shift_data()) == ch2_no_avg.n_channels
    assert len(ch2_single.get_shift_data()) == ch2_single.n_channels
    assert len(ch1_single.get_shift_data()) == 0


def test_data_injection():
    """Test injection functions for channel names and voxel (calibration)."""
    ch4 = PSFData(omero_4ch_multi_roi_full_kv)

    # Inject channel names      ----------------------------------------------
    # Inject wrong number of channel names does not modify the object
    ch4.inject_channel_names(["DAPI", "GFP", "RFP"])
    assert "DAPI" not in ch4.channel_names
    assert "DAPI" not in ch4.get_fwhm_data().keys()
    assert "C1" in ch4.channel_names
    assert "C1" in ch4.get_fwhm_data().keys()
    # Iject duplicate names (correct number) -> does not modify object
    ch4.inject_channel_names(["DAPI", "GFP", "RFP", "GFP"])
    assert "DAPI" not in ch4.channel_names
    assert "DAPI" not in ch4.get_fwhm_data().keys()
    assert "C1" in ch4.channel_names
    assert "C1" in ch4.get_fwhm_data().keys()

    # Check the the injection works as intended
    ch4.inject_channel_names(["DAPI", "GFP", "RFP", "NIR"])
    assert "DAPI" in ch4.channel_names
    assert "NIR" in ch4.get_fwhm_data().keys()

    # Inject voxel sizes      ------------------------------------------------
    ch4 = PSFData(omero_4ch_multi_roi_full_kv)
    ch4_dup = PSFData(omero_4ch_multi_roi_full_kv)

    # Inject only XY voxel size
    ch4.inject_voxel_size([2, 2])
    mod_val = ch4.get_shift_data()["C1"]["Shift-Z"]
    ori_val = ch4_dup.get_shift_data()["C1"]["Shift-Z"]
    assert mod_val == ori_val

    # Inject correctly
    ch4.inject_voxel_size([2, 2, 2])
    mod_val = ch4.get_shift_data()["C2"]["Shift-Z"]
    ori_val = ch4_dup.get_shift_data()["C2"]["Shift-Z"]
    assert mod_val == round(ori_val * 2, 6)
    # Reference channels (strings) should not be modified
    mod_val = ch4.get_shift_data()["C1"]["Shift-Y"]
    ori_val = ch4_dup.get_shift_data()["C1"]["Shift-Y"]
    assert mod_val == ori_val == "Reference-Y"


def test_from_dataframe():
    """Test the class-method from_dataframe."""
    # Create a dataframe from a dict
    df = pd.DataFrame(
        omero_4ch_multi_roi_full_kv.items(), columns=["Key", "Value"]
    )
    # Create PSFData object from dataframe
    ch4 = PSFData.from_dataframe(df)
    # Create PSFData object from dict
    ch4_old = PSFData(omero_4ch_multi_roi_full_kv)

    # Check that the values are the same for both
    ch4_data = ch4.get_fwhm_data()
    ch4_data_old = ch4_old.get_fwhm_data()
    for ch in ch4_data_old.keys():
        msg = f"{ch} missing in PSFData from_dataframe"
        assert ch in ch4_data.keys(), msg
    for ch, ch_val in ch4_data_old.items():
        for k, _v in ch_val.items():
            msg = f"{k} missing in PSFData from_dataframe"
            assert k in ch4_data[ch].keys(), msg
    for ch, ch_val in ch4_data_old.items():
        for k, v in ch_val.items():
            msg = f"{ch} - {k} value does not match for PSFData from_dataframe"
            assert v == ch4_data[ch].get(k), msg


def test_get_dataframes():
    """Test the getters for getting the data as dataframe."""
    # Create a dataframe from a dict
    df = pd.DataFrame(
        omero_4ch_multi_roi_full_kv.items(), columns=["Key", "Value"]
    )
    # Create PSFData object from dataframe
    ch4 = PSFData.from_dataframe(df)

    # Here some very simple tests
    fwhm = ch4.get_fwhm_dataframe()
    shift = ch4.get_shift_dataframe()
    assert isinstance(fwhm, pd.DataFrame)
    assert isinstance(shift, pd.DataFrame)
    assert len(fwhm) == len(shift)


if __name__ == "__main__":
    pass
