import os
from tqdm import tqdm
from ...Processing.dicom.dicom_processing import unpack_convert_dicom_patient, unpack_convert_dicom_investigation, convert_single_dicom_sequence
from ...Processing.identification.identification_process import identification_process

def run_cohort_patient_manual(input_folder: str, output_folder: str, conversion_method: str = "dcm2niix") -> None:
    """

    """
    patient_list_in_cohort = []
    for _, dirs, _ in os.walk(input_folder):
        for dir in dirs:
            patient_list_in_cohort.append(dir)
        break

    for patient_fn in tqdm(patient_list_in_cohort):
        run_single_patient_manual(input_folder=os.path.join(input_folder, patient_fn), output_folder=output_folder,
                                    conversion_method=conversion_method)


def run_single_patient_manual(input_folder: str, output_folder: str, conversion_method: str = "dcm2niix") -> None:
    converted_folder = os.path.join(output_folder, os.path.basename(input_folder)) if output_folder is not None else input_folder
    unpack_convert_dicom_patient(input_folder=input_folder, output_folder=converted_folder, method=conversion_method)
    identification_process(input_folder=converted_folder)
    # if OptionsConfiguration.getInstance().domain_target == "neuro":
    #     identify_sequences(input_folder=converted_folder, structure="manual")
    #     sequence_selection(input_folder=converted_folder)
    # elif OptionsConfiguration.getInstance().domain_target == "mediastinum":
    #     ct_sequence_selection(input_folder=converted_folder)


def run_single_timepoint_manual(input_folder: str, output_folder: str, conversion_method: str = "dcm2niix") -> None:
    converted_folder = os.path.join(output_folder, os.path.basename(input_folder)) if output_folder is not None else input_folder
    unpack_convert_dicom_investigation(input_folder=input_folder, output_folder=converted_folder, method=conversion_method)
    identification_process(input_folder=converted_folder)
    # if OptionsConfiguration.getInstance().domain_target == "neuro":
    #     identify_sequences(input_folder=converted_folder, structure="manual")
    #     sequence_selection(input_folder=converted_folder)
    # elif OptionsConfiguration.getInstance().domain_target == "mediastinum":
    #     ct_sequence_selection_ts(input_folder=converted_folder)


def run_single_image_manual(input_folder: str, output_folder: str, conversion_method: str = "dcm2niix") -> None:
    converted_folder = os.path.join(output_folder, os.path.basename(input_folder)) if output_folder is not None else input_folder
    convert_single_dicom_sequence(input_folder=input_folder, output_folder=converted_folder, method=conversion_method)
    identification_process(input_folder=converted_folder)
    # if OptionsConfiguration.getInstance().domain_target == "neuro":
    #     identify_sequences(input_folder=converted_folder, structure="manual")
