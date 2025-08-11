import traceback
import logging
import os

from sklearn.externals.array_api_extra.testing import override
from tqdm import tqdm
from .Processing.dicom_processing import unpack_convert_dicom_folder_sectra_cdviewer, convert_single_dicom_sequence, unpack_convert_dicom_investigation, unpack_convert_dicom_patient
from .Processing.mri_sequence_processing import identify_sequences, sequence_selection, sequence_selection_ts


def run_sectra_cdmedia(input_folder: str, input_category: str, output_folder: str, conversion_method: str = "dcm2niix",
                       override: bool = False) -> None:
    if input_category == "cohort_patient":
        __run_cohort_patient_sectra_cdmedia(input_folder=input_folder, output_folder=output_folder,
                                            conversion_method=conversion_method, override=override)
    elif input_category == "single_patient":
        __run_single_patient_sectra_cdmedia(input_folder=input_folder, output_folder=output_folder,
                                            conversion_method=conversion_method, override=override)
    else:
        logging.error(f'The provided input category {input_category} is not handled for a SECTRA CD '
                      f'Media folder structure. Please select from [cohort_patient, single_patient].')


def __run_cohort_patient_sectra_cdmedia(input_folder: str, output_folder: str, conversion_method: str = "dcm2niix",
                                        override: bool = False) -> None:
    """

    """
    patient_list_in_cohort = []
    for _, dirs, _ in os.walk(input_folder):
        for dir in dirs:
            patient_list_in_cohort.append(dir)
        break

    for patient_fn in tqdm(patient_list_in_cohort):
        __run_single_patient_sectra_cdmedia(input_folder=os.path.join(input_folder, patient_fn),
                                            output_folder=output_folder, conversion_method=conversion_method,
                                            override=override)


def __run_single_patient_sectra_cdmedia(input_folder: str, output_folder: str, conversion_method: str = "dcm2niix",
                                        override: bool = False) -> None:
    converted_folder = os.path.join(output_folder, os.path.basename(input_folder)) if output_folder is not None else input_folder
    unpack_convert_dicom_folder_sectra_cdviewer(input_folder=input_folder, output_folder=converted_folder,
                                                method=conversion_method, override=override)
    identify_sequences(input_folder=converted_folder, structure="sectra_cdmedia", override=override)
    sequence_selection(input_folder=converted_folder, override=override)


def run_manual_structure(input_folder: str, input_category: str, output_folder: str,
                         conversion_method: str = "dcm2niix", override: bool = False) -> None:
    if input_category == "cohort_patient":
        __run_cohort_patient_manual(input_folder=input_folder, output_folder=output_folder,
                                    conversion_method=conversion_method, override=override)
    elif input_category == "single_patient":
        __run_single_patient_manual(input_folder=input_folder, output_folder=output_folder,
                                    conversion_method=conversion_method, override=override)
    elif input_category == "single_timepoint":
        __run_single_timepoint_manual(input_folder=input_folder, output_folder=output_folder,
                                      conversion_method=conversion_method, override=override)
    elif input_category == "single_image":
        __run_single_image_manual(input_folder=input_folder, output_folder=output_folder,
                                  conversion_method=conversion_method, override=override)
    else:
        logging.error(f"Provided input_category option {input_category} is not supported."
                      f" Please select from [cohort_patient, single_patient, single_timepoint, single_image]")
        raise ValueError(f"Provided input_category option {input_category} is not supported."
                      f" Please select from [cohort_patient, single_patient, single_timepoint, single_image]")


def __run_cohort_patient_manual(input_folder: str, output_folder: str, conversion_method: str = "dcm2niix",
                                override: bool = False) -> None:
    """

    """
    patient_list_in_cohort = []
    for _, dirs, _ in os.walk(input_folder):
        for dir in dirs:
            patient_list_in_cohort.append(dir)
        break

    for patient_fn in tqdm(patient_list_in_cohort):
        __run_single_patient_manual(input_folder=os.path.join(input_folder, patient_fn), output_folder=output_folder,
                                    conversion_method=conversion_method, override=override)


def __run_single_patient_manual(input_folder: str, output_folder: str, conversion_method: str = "dcm2niix",
                                override: bool = False) -> None:
    converted_folder = os.path.join(output_folder, os.path.basename(input_folder)) if output_folder is not None else input_folder
    unpack_convert_dicom_patient(input_folder=input_folder, output_folder=converted_folder, method=conversion_method,
                                 override=override)
    identify_sequences(input_folder=converted_folder, structure="manual")
    sequence_selection(input_folder=converted_folder, override=override)


def __run_single_timepoint_manual(input_folder: str, output_folder: str, conversion_method: str = "dcm2niix",
                                  override: bool = False) -> None:
    converted_folder = os.path.join(output_folder, os.path.basename(input_folder)) if output_folder is not None else input_folder
    unpack_convert_dicom_investigation(input_folder=input_folder, output_folder=converted_folder, method=conversion_method,
                                       override=override)
    identify_sequences(input_folder=converted_folder, structure="manual")
    sequence_selection_ts(input_folder=converted_folder, override=override)


def __run_single_image_manual(input_folder: str, output_folder: str, conversion_method: str = "dcm2niix",
                              override: bool = False) -> None:
    converted_folder = os.path.join(output_folder, os.path.basename(input_folder)) if output_folder is not None else input_folder
    convert_single_dicom_sequence(input_folder=input_folder, output_folder=converted_folder, method=conversion_method,
                                  override=override)
    identify_sequences(input_folder=converted_folder, structure="manual")
