from collections import Counter
import os
import SimpleITK as sitk
import datetime
import json
import shutil
import subprocess
import traceback
import logging
import pandas as pd
import numpy as np
import pydicom
import tqdm
from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.pixel_data_handlers.util import apply_modality_lut
from pydicom.uid import ExplicitVRLittleEndian, generate_uid
from ...Utils.io_utils import safename_formatting, sanitize_filename
from ...Utils.OptionsConfiguration import OptionsConfiguration
from ...Utils.dicom_utils import *
from conversion_sectra import *


def run_sectra_cdmedia(input_folder: str, output_folder: str, conversion_method: str = "dcm2niix") -> None:
    if OptionsConfiguration.getInstance().scope == "cohort":
        run_cohort_patient_sectra_cdmedia(input_folder=input_folder, output_folder=output_folder,
                                            conversion_method=conversion_method)
    elif OptionsConfiguration.getInstance().scope == "patient":
        run_single_patient_sectra_cdmedia(input_folder=input_folder, output_folder=output_folder,
                                            conversion_method=conversion_method)
    else:
        logging.error(f'The provided input category {OptionsConfiguration.getInstance().scope} is not handled for'
                      f' a SECTRA CD Media folder structure. Please select from [cohort, patient].')
        
def unpack_convert_dicom_patient(input_folder: str, output_folder: str = None, method: str = 'dcm2niix') -> None:
    timestamp_dirs = []
    for _, dirs, _ in os.walk(input_folder):
        for name in dirs:
            timestamp_dirs.append(name)
        break

    # Collecting each investigation for the current patient
    for ts in timestamp_dirs:
        ts_dir = os.path.join(input_folder, ts, 'dicom') if os.path.exists(os.path.join(input_folder, ts, 'dicom')) else os.path.join(input_folder, ts)
        ts_output_folder = os.path.join(output_folder, ts)
        os.makedirs(ts_output_folder, exist_ok=True)
        unpack_convert_dicom_investigation(input_folder=ts_dir, output_folder=ts_output_folder, method=method)

def unpack_convert_dicom_investigation(input_folder: str, output_folder: str = None, method: str = 'dcm2niix') -> None:
    override = OptionsConfiguration.getInstance().override
    input_folder = os.path.join(input_folder, 'dicom') if os.path.exists(os.path.join(input_folder, 'dicom')) else input_folder
    investigation_dirs = []
    for _, dirs, _ in os.walk(input_folder):
        for name in dirs:
            investigation_dirs.append(name)
        break

    # Collecting each investigation for the current patient
    for inv in investigation_dirs:
        inv_dir = os.path.join(input_folder, inv)
        inv_output_folder = os.path.join(output_folder, inv)
        try:
            if os.path.exists(inv_output_folder):
                if not override:
                    logging.info(f"Skipping extraction - folder already exists at {inv_output_folder}")
                    continue
                else:
                    shutil.rmtree(inv_output_folder)
            os.makedirs(inv_output_folder)
            convert_single_dicom_sequence(input_folder=inv_dir, output_folder=inv_output_folder, method=method)
        except Exception as e:
            if os.path.exists(inv_output_folder) and len(os.listdir(inv_output_folder)) == 0:
                shutil.rmtree(inv_output_folder)


def convert_single_dicom_sequence(input_folder: str, output_folder: str = None, method: str = 'dcm2niix') -> None:
    """
    """
    try:
        from .conversion_anonymised import reconstruct_raw_dicom
        if OptionsConfiguration.getInstance().dicom_fully_anonymised:
            reconstruct_raw_dicom(input_folder=input_folder, dest_folder=output_folder)
            input_folder = output_folder
        reconstruct_structured_dicom(input_folder=input_folder, output_folder=output_folder, method=method)
    except Exception as e:
        raise ValueError(f"Single DICOM conversion failed with {e}.")



def reconstruct_structured_dicom(input_folder: str, output_folder: str, method: str = "dcm2niix") -> None:
    """
        # @TODO. assert to make sure there are no other directories inside, only .dcm files
    """
    try:
        override = OptionsConfiguration.getInstance().override
        reader = sitk.ImageSeriesReader()
        serie_names = reader.GetGDCMSeriesIDs(input_folder)

        # dicom_names = reader.GetGDCMSeriesFileNames(current_dicom_investigation_path, useSeriesDetails=True)
        # tmp_data = Path(current_dicom_investigation_path)
        # tmp_dicom_names = list(tmp_data.glob('*'))
        # dicom_names_set = [dicom_names]
        # if len(tmp_dicom_names) > len(dicom_names):
        #     dicom_names_set = [[str(x) for x in tmp_dicom_names[:len(dicom_names)]],
        #                        [str(x) for x in tmp_dicom_names[len(dicom_names):]]]
        #     print('Nested images into one DICOM sub-folder......')

        for s, serie in enumerate(serie_names):
            dicom_names = reader.GetGDCMSeriesFileNames(input_folder, serie)
            reader.SetFileNames(dicom_names)
            reader.LoadPrivateTagsOn()
            reader.SetMetaDataDictionaryArrayUpdate(True)

            tmp = reader.Execute()
            date = datetime.datetime.strptime(reader.GetMetaData(0, '0008|0021')[0:8], '%Y%m%d')
    except Exception as e:
        logging.error(f"Reading DICOM metadata tags for {input_folder} failed with:\n {e}")
        # print('Patient {}, could not process DICOM'.format(uid))
        # print('Collected exception: {}'.format(e.args[0]))

    try:
        execute_and_output_reader(input_folder=input_folder, output_folder=output_folder, timestamp=None, reader=reader, index=0, method=method)
        # image = reader.Execute()
        # existing_dicom_keys = reader.GetMetaDataKeys(0)
        # # metatags = [[k, reader.GetMetaData(0, k)] for k in existing_dicom_keys]
        # # Trick to prevent weird encoding from crashing the conversion process
        # metatags = [[k, str(reader.GetMetaData(0, k)).encode('utf-8', 'replace').decode('utf-8')] for k in existing_dicom_keys]
        # metatags_df = pd.DataFrame(metatags, columns=['Tag', 'Value'])
        # # for k in existing_dicom_keys:
        # #     v = reader.GetMetaData(0, k)
        # #     print("({0}) = = \"{1}\"".format(k, v))

        # image_dname = 'unknown'
        # if '0008|103e' in existing_dicom_keys:
        #     image_dname = reader.GetMetaData(0, '0008|103e').strip()
        #     image_dname = '-'.join(image_dname.split()).replace('.', '-').replace('/', '-').replace('\\', '-')
        # elif '0008|0008' in existing_dicom_keys:
        #     image_dname = reader.GetMetaData(0, '0008|0008').strip().replace('\\', '-').replace('.', '-').replace('/', '-')

        # clean_image_dname = safename_formatting(image_dname)
        # image_name =  clean_image_dname + '.nii.gz'
        # dump_image_path = os.path.join(output_folder, image_name)
        # os.makedirs(os.path.dirname(dump_image_path), exist_ok=True)
        # if not os.path.isdir(os.path.dirname(dump_image_path)):
        #     os.makedirs(os.path.dirname(dump_image_path))

        # if method == 'sitk':
        #     sitk.WriteImage(image, dump_image_path)
        # elif method == 'dcm2niix':
        #     tmp_folder = os.path.join(os.path.dirname(dump_image_path), 'tmp')
        #     output_filename = os.path.join(tmp_folder, 'correct_CT')
        #     if not os.path.isdir(tmp_folder):
        #         os.mkdir(tmp_folder)

        #     exec_filepath = os.path.join(os.path.dirname(__file__), "..", "MRIcroGL", "Resources", 'dcm2niix')
        #     try:
        #         subprocess.call(
        #             ["{exec}".format(exec=exec_filepath),
        #              "-o", "{output}".format(output=os.path.dirname(output_filename)),
        #              "-f", "{filename}".format(filename=os.path.basename(output_filename)),
        #              "-z", "y",
        #              "{input}".format(input=os.path.dirname(reader.GetFileNames()[0]))])
        #     except Exception:
        #         if os.path.isdir(tmp_folder):
        #             shutil.rmtree(tmp_folder)
        #         raise ValueError("DICOM to nifti conversion failed for folder: {}".format(input_folder))

        #     created_filename = None
        #     for _, _, files in os.walk(tmp_folder):
        #         for f in files:
        #             if f.split('.')[-1] == 'gz':
        #                 created_filename = f
        #         break

        #     if created_filename is None:
        #         if os.path.isdir(tmp_folder):
        #             shutil.rmtree(tmp_folder)
        #         return

        #     output_filename = os.path.join(tmp_folder, created_filename)
        #     #
        #     # if not os.path.exists(output_filename + '.nii.gz'):
        #     #     output_filename = output_filename + '_e1'
        #     #     if not os.path.exists(output_filename + '.nii.gz'):
        #     #         print('Could not find any reconverted CT for patient {}'.format(uid))
        #     #         continue

        #     # shutil.move(src=output_filename + '.nii.gz', dst=dump_image_path)
        #     shutil.move(src=output_filename, dst=dump_image_path)
        #     if os.path.isdir(tmp_folder):
        #         shutil.rmtree(tmp_folder)
        # try:
        #     meta_dump_path = os.path.join(os.path.dirname(dump_image_path), 'Meta',
        #                                   os.path.basename(dump_image_path).split['.'][0] + '_metadata.csv')
        #     os.makedirs(os.path.dirname(meta_dump_path), exist_ok=True)
        #     metatags_df.to_csv(meta_dump_path, index=False, encoding='utf-8')
        # except Exception as e:
        #     # metatags = [[k, str.encode(reader.GetMetaData(0, k)).decode('utf8', 'surrogateescape')] for k in
        #     #             existing_dicom_keys]
        #     logging.warning(f"DICOM metadata tags with problematic encoding detected in: {input_folder} with {e}")
    except Exception as e:
        logging.error(f"Conversion failed for folder: {input_folder} failed with:\n {e}")