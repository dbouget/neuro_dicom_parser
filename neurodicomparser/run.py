import traceback
import logging
import os

from tqdm import tqdm
from .Processing.dicom_processing import unpack_convert_dicom_folder_sectra_cdviewer, convert_single_dicom_sequence, unpack_convert_dicom_investigation, unpack_convert_dicom_patient
from .Processing.mri_sequence_processing import identify_sequences, sequence_selection, sequence_selection_ts
from .Processing.ct_sequence_processing import ct_sequence_selection, ct_sequence_selection_ts
from .Utils.OptionsConfiguration import OptionsConfiguration


def run_parser(config_fn: str) -> None:
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


def run_sectra_cdmedia(input_folder: str, output_folder: str, conversion_method: str = "dcm2niix") -> None:
    if OptionsConfiguration.getInstance().scope == "cohort":
        __run_cohort_patient_sectra_cdmedia(input_folder=input_folder, output_folder=output_folder,
                                            conversion_method=conversion_method)
    elif OptionsConfiguration.getInstance().scope == "patient":
        __run_single_patient_sectra_cdmedia(input_folder=input_folder, output_folder=output_folder,
                                            conversion_method=conversion_method)
    else:
        logging.error(f'The provided input category {OptionsConfiguration.getInstance().scope} is not handled for'
                      f' a SECTRA CD Media folder structure. Please select from [cohort, patient].')


def __run_cohort_patient_sectra_cdmedia(input_folder: str, output_folder: str, conversion_method: str = "dcm2niix") -> None:
    """

    """
    patient_list_in_cohort = []
    for _, dirs, _ in os.walk(input_folder):
        for dir in dirs:
            patient_list_in_cohort.append(dir)
        break

    for patient_fn in tqdm(patient_list_in_cohort):
        __run_single_patient_sectra_cdmedia(input_folder=os.path.join(input_folder, patient_fn),
                                            output_folder=output_folder, conversion_method=conversion_method)


def __run_single_patient_sectra_cdmedia(input_folder: str, output_folder: str, conversion_method: str = "dcm2niix") -> None:
    converted_folder = os.path.join(output_folder, os.path.basename(input_folder)) if output_folder is not None else input_folder
    unpack_convert_dicom_folder_sectra_cdviewer(input_folder=input_folder, output_folder=converted_folder,
                                                method=conversion_method)
    identify_sequences(input_folder=converted_folder, structure="sectra_cdmedia")
    sequence_selection(input_folder=converted_folder)


def run_manual_structure(input_folder: str, output_folder: str, conversion_method: str = "dcm2niix") -> None:
    if OptionsConfiguration.getInstance().scope == "patient":
        __run_cohort_patient_manual(input_folder=input_folder, output_folder=output_folder,
                                    conversion_method=conversion_method)
    elif OptionsConfiguration.getInstance().scope == "patient":
        __run_single_patient_manual(input_folder=input_folder, output_folder=output_folder,
                                    conversion_method=conversion_method)
    elif OptionsConfiguration.getInstance().scope == "timepoint":
        __run_single_timepoint_manual(input_folder=input_folder, output_folder=output_folder,
                                      conversion_method=conversion_method)
    elif OptionsConfiguration.getInstance().scope == "image":
        __run_single_image_manual(input_folder=input_folder, output_folder=output_folder,
                                  conversion_method=conversion_method)
    else:
        logging.error(f"Provided input_category option {OptionsConfiguration.getInstance().scope} is not supported."
                      f" Please select from [cohort, patient, timepoint, image]")
        raise ValueError(f"Provided input_category option {OptionsConfiguration.getInstance().scope} is not supported."
                      f" Please select from [cohort, patient, timepoint, image]")


def __run_cohort_patient_manual(input_folder: str, output_folder: str, conversion_method: str = "dcm2niix") -> None:
    """

    """
    patient_list_in_cohort = []
    for _, dirs, _ in os.walk(input_folder):
        for dir in dirs:
            patient_list_in_cohort.append(dir)
        break

    for patient_fn in tqdm(patient_list_in_cohort):
        __run_single_patient_manual(input_folder=os.path.join(input_folder, patient_fn), output_folder=output_folder,
                                    conversion_method=conversion_method)


def __run_single_patient_manual(input_folder: str, output_folder: str, conversion_method: str = "dcm2niix") -> None:
    converted_folder = os.path.join(output_folder, os.path.basename(input_folder)) if output_folder is not None else input_folder
    unpack_convert_dicom_patient(input_folder=input_folder, output_folder=converted_folder, method=conversion_method)

    if OptionsConfiguration.getInstance().domain_target == "neuro":
        identify_sequences(input_folder=converted_folder, structure="manual")
        sequence_selection(input_folder=converted_folder)
    elif OptionsConfiguration.getInstance().domain_target == "mediastinum":
        ct_sequence_selection(input_folder=converted_folder)


def __run_single_timepoint_manual(input_folder: str, output_folder: str, conversion_method: str = "dcm2niix") -> None:
    converted_folder = os.path.join(output_folder, os.path.basename(input_folder)) if output_folder is not None else input_folder
    unpack_convert_dicom_investigation(input_folder=input_folder, output_folder=converted_folder, method=conversion_method)
    if OptionsConfiguration.getInstance().domain_target == "neuro":
        identify_sequences(input_folder=converted_folder, structure="manual")
        sequence_selection(input_folder=converted_folder)
    elif OptionsConfiguration.getInstance().domain_target == "mediastinum":
        ct_sequence_selection_ts(input_folder=converted_folder)


def __run_single_image_manual(input_folder: str, output_folder: str, conversion_method: str = "dcm2niix") -> None:
    converted_folder = os.path.join(output_folder, os.path.basename(input_folder)) if output_folder is not None else input_folder
    convert_single_dicom_sequence(input_folder=input_folder, output_folder=converted_folder, method=conversion_method)
    if OptionsConfiguration.getInstance().domain_target == "neuro":
        identify_sequences(input_folder=converted_folder, structure="manual")
