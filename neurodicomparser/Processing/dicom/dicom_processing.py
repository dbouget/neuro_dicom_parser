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
from .conversion_sectra import *


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
    """
    
    """
    timestamp_dirs = list_subdirs(input_folder)

    # Collecting each investigation for the current patient
    for ts in timestamp_dirs:
        ts_dir = os.path.join(input_folder, ts, 'dicom') if os.path.exists(os.path.join(input_folder, ts, 'dicom')) else os.path.join(input_folder, ts)
        ts_output_folder = os.path.join(output_folder, ts)
        os.makedirs(ts_output_folder, exist_ok=True)
        unpack_convert_dicom_investigation(input_folder=ts_dir, output_folder=ts_output_folder, method=method)

def unpack_convert_dicom_investigation(input_folder: str, output_folder: str = None, method: str = 'dcm2niix') -> None:
    override = OptionsConfiguration.getInstance().override
    input_folder = os.path.join(input_folder, 'dicom') if os.path.exists(os.path.join(input_folder, 'dicom')) else input_folder
    investigation_dirs = list_subdirs(input_folder)

    if len(investigation_dirs) == 0 and os.listdir(input_folder) != 0:
        reconstruct_unstructured_dicom(input_folder=input_folder, output_folder=output_folder, method=method)
    else:
        # Collecting each investigation for the current patient
        try:
            readers = []
            timestamps = []
            primary_date = None
            for inv in investigation_dirs:
                inv_dir = os.path.join(input_folder, inv)
                try:
                    if OptionsConfiguration.getInstance().dicom_fully_anonymised:
                        from ...Processing.dicom.conversion_anonymised import reconstruct_raw_dicom
                        conv_folder = reconstruct_raw_dicom(input_folder=inv_dir, dest_folder=output_folder)
                        inv_dir = conv_folder
                        logging.warning("Use-case never tried, must be confirmed: anonymized DICOM, manual patient")
                    reader = sitk.ImageSeriesReader()
                    serie_names = reader.GetGDCMSeriesIDs(inv_dir)
                    for s, serie in enumerate(serie_names):
                        dicom_names = reader.GetGDCMSeriesFileNames(inv_dir, serie)
                        reader.SetFileNames(dicom_names)
                        reader.LoadPrivateTagsOn()
                        reader.SetMetaDataDictionaryArrayUpdate(True)
                        readers.append(reader)

                        # Read metadata from ONE file only — tags are series-level, not slice-level
                        single_ds = pydicom.dcmread(dicom_names[0], stop_before_pixels=True)
                        primary = is_dicom_acquisition_primary(single_ds)
                        date = extract_dicom_date(single_ds)

                        if date:
                            timestamps.append(date)
                        if primary_date is None and primary and date is not None:
                            primary_date = date
                except Exception as e:
                    logging.error(f"Reading DICOM metadata tags for {inv_dir} failed with:\n {e}")
                    raise
            if len(timestamps) == 0:
                timestamp =  "unknown"
            elif primary_date is not None:
                timestamp = primary_date
            else:
                counts = Counter(timestamps)
                timestamp = counts.most_common(1)[0][0]
            logging.info(f'Inclusion for timestamp: {timestamp}')
            for r, reader in enumerate(readers):
                try:
                    execute_and_output_reader(input_folder=input_folder, output_folder=output_folder, 
                                            timestamp=timestamp, reader=reader, method=method)
                except Exception as e:
                    print('Collected exception: {}'.format(e.args[0]))
                    print('{}'.format(traceback.format_exc()))
                    continue
        except Exception as e:
            raise


def convert_single_dicom_sequence(input_folder: str, output_folder: str = None, method: str = 'dcm2niix') -> None:
    """

    """
    try:
        from .conversion_anonymised import reconstruct_raw_dicom
        if OptionsConfiguration.getInstance().dicom_fully_anonymised:
            conv_folder = reconstruct_raw_dicom(input_folder=input_folder, dest_folder=output_folder)
            input_folder = conv_folder
        reconstruct_structured_dicom(input_folder=input_folder, output_folder=output_folder, method=method)
    except Exception as e:
        raise ValueError(f"Single DICOM conversion failed with {e}.")



def reconstruct_structured_dicom(input_folder: str, output_folder: str, method: str = "dcm2niix") -> None:
    """
        # @TODO. assert to make sure there are no other directories inside, only .dcm files
    """
    try:
        timestamps = []
        primary_date = None
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

            # Read metadata from ONE file only — tags are series-level, not slice-level
            single_ds = pydicom.dcmread(dicom_names[0], stop_before_pixels=True)
            primary = is_dicom_acquisition_primary(single_ds)
            date = extract_dicom_date(single_ds)

            if date:
                timestamps.append(date)
            if primary_date is None and primary and date is not None:
                primary_date = date
    except Exception as e:
        logging.error(f"Reading DICOM metadata tags for {input_folder} failed with:\n {e}")
        # print('Patient {}, could not process DICOM'.format(uid))
        # print('Collected exception: {}'.format(e.args[0]))

    try:
        if len(timestamps) == 0:
            timestamp =  "unknown"
        elif primary_date is not None:
            timestamp = primary_date
        else:
            counts = Counter(timestamps)
            timestamp = counts.most_common(1)[0][0]
        logging.info(f'Inclusion for timestamp: {timestamp}')
        execute_and_output_reader(input_folder=input_folder, output_folder=output_folder, timestamp=None,
                                  reader=reader, method=method)
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

def reconstruct_unstructured_dicom(input_folder: str, output_folder: str, method: str = "dcm2niix") -> None:
    """

    """
    tmp_folder = os.path.join(os.path.dirname(output_folder), 'tmp')
    try:
        timestamps = []
        if method == "dcm2niix":     
            output_filename = os.path.join(tmp_folder, 'correct_CT')
            if not os.path.isdir(tmp_folder):
                os.mkdir(tmp_folder)
            exec_filepath = os.path.join(os.path.dirname(__file__), "..", "..", "MRIcroGL", "Resources", 'dcm2niix')
            try:
                subprocess.call(
                    ["{exec}".format(exec=exec_filepath),
                        "-o", "{output}".format(output=os.path.dirname(output_filename)),
                        "-f", "{filename}".format(filename=os.path.basename(output_filename)),
                        "-z", "y",
                        "{input}".format(input=input_folder)])
            except Exception:
                if os.path.isdir(tmp_folder):
                    shutil.rmtree(tmp_folder)
                raise ValueError("DICOM to nifti conversion failed for folder: {}".format(input_folder))  
            series_map = group_dicoms_by_composite_key(input_folder)
            for nii_file in sorted(os.listdir(tmp_folder)):
                if not nii_file.endswith(".nii.gz"):
                    continue
                logging.info(f"Nifti file {nii_file}")
                json_path = os.path.join(tmp_folder, nii_file.replace(".nii.gz", ".json"))
                if not os.path.exists(json_path):
                    continue

                with open(json_path) as f:
                    sidecar = json.load(f)

                key = make_sidecar_key(sidecar)
                source_files = series_map.get(key, [])

                if not source_files:
                    print(f"Warning: no DICOMs found for SeriesNumber {key[0]}")
                    continue

                # Read metadata from ONE file only — tags are series-level, not slice-level
                single_ds = pydicom.dcmread(source_files[0], stop_before_pixels=True)
                metatags = {
                    f"{elem.tag.group:04x}|{elem.tag.element:04x}": 
                        str(elem.value).encode('utf-8', 'replace').decode('utf-8')
                    for elem in single_ds if elem.keyword != 'PixelData'
                }

                primary = is_dicom_acquisition_primary(single_ds)
                date = extract_dicom_date(single_ds)
                if primary:
                    timestamps.append(date)
                sequence_readable_name = None
                try:
                    sequence_readable_name = build_sequence_readable_name(metatags=metatags, input_folder=input_folder)
                except Exception as e:
                    sequence_readable_name = os.path.basename(input_folder)
                sequence_readable_name = sanitize_filename(sequence_readable_name)
                dump_image_path = os.path.join(output_folder, "Unknown_date", sequence_readable_name + '.nii.gz')

                output_filename = os.path.join(tmp_folder, nii_file)
                os.makedirs(os.path.dirname(dump_image_path), exist_ok=True)
                shutil.copyfile(src=output_filename, dst=dump_image_path)
                metadata_filename = os.path.join(os.path.dirname(dump_image_path), "Meta",
                                    os.path.basename(dump_image_path).split('.')[0] + '_metadata.csv')
                os.makedirs(os.path.dirname(metadata_filename), exist_ok=True)
                pd.DataFrame(list(metatags.items()), columns=['Tag', 'Value']).to_csv(metadata_filename, index=False, encoding='utf-8')
        else:
            raise ValueError(f"Must run with dcm2niix, use-case with {method} not implemented yet")
    except Exception as e:
        if os.path.exists(tmp_folder):
            shutil.rmtree(tmp_folder)
        raise ValueError(f"All in one folder conversion failed with {e}")

    if len(timestamps) != 0:
        try:
            counts = Counter(timestamps)
            timestamp = counts.most_common(1)[0][0]
            current_dir = os.path.join(output_folder, "Unknown_date")
            new_dir = os.path.join(output_folder, timestamp)
            shutil.move(src=current_dir, dst=new_dir)
        except Exception as e:
            raise ValueError(f"Moving produced directory to timestamped version failed with {e}")

    if os.path.exists(tmp_folder):
        shutil.rmtree(tmp_folder)