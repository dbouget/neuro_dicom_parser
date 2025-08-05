import traceback
import logging
import os
from tqdm import tqdm
from .Processing.dicom_processing import unpack_convert_dicom_folder
from .Processing.mri_sequence_processing import identify_sequences, sequence_selection


def run_cohort(input_folder: str, output_folder: str, logging_filename: str = None) -> None:
    """

    """
    patient_list_in_cohort = []
    for _, dirs, _ in os.walk(input_folder):
        for dir in dirs:
            patient_list_in_cohort.append(dir)
        break

    for patient_fn in tqdm(patient_list_in_cohort):
        run_single(input_folder=os.path.join(input_folder, patient_fn), output_folder=output_folder,
                   logging_filename=logging_filename)


def run_single(input_folder: str, output_folder: str, logging_filename: str = None) -> None:
    converted_folder = os.path.join(output_folder, os.path.basename(input_folder)) if output_folder is not None else input_folder
    unpack_convert_dicom_folder(input_folder=input_folder,
                                output_folder=converted_folder,
                                method='dcm2niix')
    identify_sequences(input_folder=converted_folder)
    sequence_selection(input_folder=converted_folder)