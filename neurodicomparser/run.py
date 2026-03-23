import traceback
import logging
import os
import sys

from tqdm import tqdm
from .Processing.dicom.dicom_processing import run_sectra_cdmedia
from .Processing.dicom.conversion_custom import run_cohort_patient_manual, run_single_patient_manual, run_single_timepoint_manual, run_single_image_manual
from .Utils.OptionsConfiguration import OptionsConfiguration
from .Utils.ensure_dcm2nii_present import ensure_dcm2nii_present
from .Utils.ensure_models_present import ensure_models_present


def run_parser(config_fn: str) -> None:
    try:
        ensure_models_present()
        ensure_dcm2nii_present()
    except Exception as e:
        logging.error(f'Downloading the mandatory resources failed with: {e}')
        sys.exit()

    try:
        OptionsConfiguration.getInstance().init(config_fn=config_fn)
        input_folder = OptionsConfiguration.getInstance().input_folder
        output_folder = OptionsConfiguration.getInstance().output_folder
        conversion_method = OptionsConfiguration.getInstance().dicom_conversion_method
        if OptionsConfiguration.getInstance().dicom_structure == "sectra_cdmedia":
            run_sectra_cdmedia(input_folder=input_folder, output_folder=output_folder,
                               conversion_method=conversion_method)
        elif OptionsConfiguration.getInstance().dicom_structure == "manual":
            run_manual_structure(input_folder=input_folder, output_folder=output_folder,
                                 conversion_method=conversion_method)
    except Exception as e:
        raise ValueError(f"Running DICOM parser failed with {e}")



def run_manual_structure(input_folder: str, output_folder: str, conversion_method: str = "dcm2niix") -> None:
    """
    Running DICOM to Nifti conversion for a folder manually put together where the content can be a single DICOM volume, 
    a set if acquisition for a single date, a set of acquisitions over time, or a set of patient folders.
    """
    if OptionsConfiguration.getInstance().content_granularity == "cohort":
        run_cohort_patient_manual(input_folder=input_folder, output_folder=output_folder,
                                    conversion_method=conversion_method)
    elif OptionsConfiguration.getInstance().content_granularity == "patient":
        run_single_patient_manual(input_folder=input_folder, output_folder=output_folder,
                                    conversion_method=conversion_method)
    elif OptionsConfiguration.getInstance().content_granularity == "timepoint":
        run_single_timepoint_manual(input_folder=input_folder, output_folder=output_folder,
                                      conversion_method=conversion_method)
    elif OptionsConfiguration.getInstance().content_granularity == "image":
        run_single_image_manual(input_folder=input_folder, output_folder=output_folder,
                                  conversion_method=conversion_method)
    else:
        logging.error(f"Provided input_category option {OptionsConfiguration.getInstance().content_granularity} is not supported."
                      f" Please select from [cohort, patient, timepoint, image]")
        raise ValueError(f"Provided input_category option {OptionsConfiguration.getInstance().content_granularity} is not supported."
                      f" Please select from [cohort, patient, timepoint, image]")
