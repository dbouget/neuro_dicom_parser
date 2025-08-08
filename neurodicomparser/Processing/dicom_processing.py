import os
import SimpleITK as sitk
import datetime
import shutil
import subprocess
import traceback
import logging
import pandas as pd


def unpack_convert_dicom_folder_sectra_cdviewer(input_folder: str, output_folder: str = None,
                                                method: str = 'dcm2niix', override: bool = False) -> None:
    """
    Iterate over the different sub-folders of a main patient folder, and converts to nifti
    every found DICOM sequences, keeping the sub-folders structure.
    :param input_folder: folder root for a patient, expected to contain a DICOM sub-folder.
    :param method: preferred way to convert a DICOM volume to Nifti: [dcm2niix, sitk]
    :param output_folder: a DICOM-conv folder is created at the output_folder folder. This new folder will contain
     all converted volumes, along with DICOM metadata in csv files.
    """
    patient_base_dicom = os.path.join(input_folder, 'DICOM')
    if not os.path.exists(patient_base_dicom):
        print('No existing DICOM folder in {}'.format(input_folder))
        return

    output_root = os.path.join(output_folder, 'DICOM-conv')
    # Skipping patients where the conversion has already been done, unless specified otherwise
    if os.path.exists(output_root) and not override:
        logging.info(f"Skipping DICOM to nifti conversion, output folder already exists at {output_root}")
        return
    os.makedirs(output_root, exist_ok=True)

    main_dicom_dir = []
    for _, dirs, _ in os.walk(patient_base_dicom):
        for name in dirs:
            main_dicom_dir.append(name)
        break

    if len(main_dicom_dir) == 0:
        return

    main_dicom_investigations = []
    main_dicom_order = 0
    for mdd in main_dicom_dir:
        main_dicom_order = main_dicom_order + 1
        patient_base_main_dicom = os.path.join(patient_base_dicom, mdd)
        timestamp_dicom_sub_dirs = []
        for _, dirs, _ in os.walk(patient_base_main_dicom):
            for name in dirs:
                timestamp_dicom_sub_dirs.append(name)
            break

        dicom_investigations = {}
        # Iterating over each timestamp
        ts_order = 0
        for subdir in timestamp_dicom_sub_dirs:
            ts_order = ts_order + 1
            timestamp = None
            investigations_for_timestamp = []
            timestamp_base_main_dicom = os.path.join(patient_base_main_dicom, subdir)
            sub_dir = []
            for _, dirs, _ in os.walk(timestamp_base_main_dicom):
                for name in dirs:
                    sub_dir.append(name)
                break

            timestamp_base_main_dicom = os.path.join(timestamp_base_main_dicom, sub_dir[0])
            investigation_dirs = []
            for _, dirs, _ in os.walk(timestamp_base_main_dicom):
                for name in dirs:
                    investigation_dirs.append(name)
                break

            # Collecting each investigation for the current patient
            for inv in investigation_dirs:
                try:
                    current_dicom_investigation_path = os.path.join(timestamp_base_main_dicom, inv)
                    reader = sitk.ImageSeriesReader()
                    serie_names = reader.GetGDCMSeriesIDs(current_dicom_investigation_path)

                    # dicom_names = reader.GetGDCMSeriesFileNames(current_dicom_investigation_path, useSeriesDetails=True)
                    # tmp_data = Path(current_dicom_investigation_path)
                    # tmp_dicom_names = list(tmp_data.glob('*'))
                    # dicom_names_set = [dicom_names]
                    # if len(tmp_dicom_names) > len(dicom_names):
                    #     dicom_names_set = [[str(x) for x in tmp_dicom_names[:len(dicom_names)]],
                    #                        [str(x) for x in tmp_dicom_names[len(dicom_names):]]]
                    #     print('Nested images into one DICOM sub-folder......')

                    for s, serie in enumerate(serie_names):
                        dicom_names = reader.GetGDCMSeriesFileNames(current_dicom_investigation_path, serie)
                        reader.SetFileNames(dicom_names)
                        reader.LoadPrivateTagsOn()
                        reader.SetMetaDataDictionaryArrayUpdate(True)
                        investigations_for_timestamp.append(reader)

                        tmp = reader.Execute()
                        date = datetime.datetime.strptime(reader.GetMetaData(0, '0008|0021')[0:8], '%Y%m%d')
                        if timestamp is None:
                            timestamp = date
                            print('Inclusion for timestamp: {}'.format(timestamp))
                except Exception as e:
                    # print('Patient {}, could not process DICOM'.format(uid))
                    # print('Collected exception: {}'.format(e.args[0]))
                    continue

            dicom_investigations[ts_order] = investigations_for_timestamp
        main_dicom_investigations.append(dicom_investigations)

    main_order = 0
    sub_folder_id = 0
    order = 1
    for dicom_investigations in main_dicom_investigations:
        main_order = main_order + 1
        for it, ts_key in enumerate(dicom_investigations.keys()):
            readers = dicom_investigations[ts_key]
            sub_folder_id = sub_folder_id + 1
            for reader in readers:
                try:
                    image = reader.Execute()
                    existing_dicom_keys = reader.GetMetaDataKeys(0)
                    # metatags = [[k, reader.GetMetaData(0, k)] for k in existing_dicom_keys]
                    # Trick to prevent weird encoding from crashing the conversion process
                    metatags = [[k, str(reader.GetMetaData(0, k)).encode('utf-8', 'replace').decode('utf-8')] for k in existing_dicom_keys]
                    metatags_df = pd.DataFrame(metatags, columns=['Tag', 'Value'])
                    # for k in existing_dicom_keys:
                    #     v = reader.GetMetaData(0, k)
                    #     print("({0}) = = \"{1}\"".format(k, v))

                    image_dname = 'unknown'
                    if '0008|103e' in existing_dicom_keys:
                        image_dname = reader.GetMetaData(0, '0008|103e').strip()
                        image_dname = '-'.join(image_dname.split()).replace('.', '-').replace('/', '-').replace('\\', '-')
                    elif '0008|0008' in existing_dicom_keys:
                        image_dname = reader.GetMetaData(0, '0008|0008').strip().replace('\\', '-').replace('.', '-').replace('/', '-')

                    image_name = str(order) + '_' + image_dname + '.nii.gz'
                    dump_image_path = os.path.join(output_root, str(sub_folder_id), image_name)
                    os.makedirs(os.path.dirname(dump_image_path), exist_ok=True)
                    if not os.path.isdir(os.path.dirname(dump_image_path)):
                        os.makedirs(os.path.dirname(dump_image_path))

                    if method == 'sitk':
                        sitk.WriteImage(image, dump_image_path)
                    elif method == 'dcm2niix':
                        tmp_folder = os.path.join(os.path.dirname(dump_image_path), 'tmp')
                        output_filename = os.path.join(tmp_folder, 'correct_CT')
                        if not os.path.isdir(tmp_folder):
                            os.mkdir(tmp_folder)

                        exec_filepath = os.path.join(os.path.dirname(__file__), "..", "MRIcroGL", "Resources", 'dcm2niix')
                        try:
                            subprocess.call(
                                ["{exec}".format(exec=exec_filepath),
                                 "-o", "{output}".format(output=os.path.dirname(output_filename)),
                                 "-f", "{filename}".format(filename=os.path.basename(output_filename)),
                                 "-z", "y",
                                 "{input}".format(input=os.path.dirname(reader.GetFileNames()[0]))])
                        except Exception:
                            if os.path.isdir(tmp_folder):
                                shutil.rmtree(tmp_folder)
                            raise ValueError("DICOM to nifti conversion failed for folder: {}".format(input_folder))

                        created_filename = None
                        for _, _, files in os.walk(tmp_folder):
                            for f in files:
                                if f.split('.')[-1] == 'gz':
                                    created_filename = f
                            break

                        if created_filename is None:
                            if os.path.isdir(tmp_folder):
                                shutil.rmtree(tmp_folder)
                            continue

                        output_filename = os.path.join(tmp_folder, created_filename)
                        #
                        # if not os.path.exists(output_filename + '.nii.gz'):
                        #     output_filename = output_filename + '_e1'
                        #     if not os.path.exists(output_filename + '.nii.gz'):
                        #         print('Could not find any reconverted CT for patient {}'.format(uid))
                        #         continue

                        # shutil.move(src=output_filename + '.nii.gz', dst=dump_image_path)
                        shutil.move(src=output_filename, dst=dump_image_path)
                        if os.path.isdir(tmp_folder):
                            shutil.rmtree(tmp_folder)
                    order = order + 1
                    try:
                        metatags_df.to_csv(dump_image_path.split('.')[0] + '_metadata.csv', index=False, encoding='utf-8')
                    except Exception as e:
                        # Some fields in the metadata have a weird encoding....
                        # metatags = [[k, str.encode(reader.GetMetaData(0, k)).decode('utf8', 'surrogateescape')] for k in
                        #             existing_dicom_keys]
                        continue
                except Exception as e:
                    print('Collected exception: {}'.format(e.args[0]))
                    print('{}'.format(traceback.format_exc()))
                    continue


def unpack_convert_dicom_patient(input_folder: str, output_folder: str = None, method: str = 'dcm2niix',
                                 override: bool = False) -> None:
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
        unpack_convert_dicom_investigation(input_folder=ts_dir, output_folder=ts_output_folder, method=method,
                                           override=override)

def unpack_convert_dicom_investigation(input_folder: str, output_folder: str = None, method: str = 'dcm2niix',
                                       override: bool = False) -> None:
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
        if os.path.exists(inv_output_folder):
            if not override:
                logging.info(f"Skipping extraction - folder already exists at {inv_output_folder}")
                continue
            else:
                shutil.rmtree(inv_output_folder)
        os.makedirs(inv_output_folder)
        convert_single_dicom_sequence(input_folder=inv_dir, output_folder=inv_output_folder, method=method,
                                      override=override)


def convert_single_dicom_sequence(input_folder: str, output_folder: str = None, method: str = 'dcm2niix',
                                  override: bool = False) -> None:
    """
    """
    # @TODO. assert to make sure there are no other directories inside, only .dcm files

    try:
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
        image = reader.Execute()
        existing_dicom_keys = reader.GetMetaDataKeys(0)
        # metatags = [[k, reader.GetMetaData(0, k)] for k in existing_dicom_keys]
        # Trick to prevent weird encoding from crashing the conversion process
        metatags = [[k, str(reader.GetMetaData(0, k)).encode('utf-8', 'replace').decode('utf-8')] for k in existing_dicom_keys]
        metatags_df = pd.DataFrame(metatags, columns=['Tag', 'Value'])
        # for k in existing_dicom_keys:
        #     v = reader.GetMetaData(0, k)
        #     print("({0}) = = \"{1}\"".format(k, v))

        image_dname = 'unknown'
        if '0008|103e' in existing_dicom_keys:
            image_dname = reader.GetMetaData(0, '0008|103e').strip()
            image_dname = '-'.join(image_dname.split()).replace('.', '-').replace('/', '-').replace('\\', '-')
        elif '0008|0008' in existing_dicom_keys:
            image_dname = reader.GetMetaData(0, '0008|0008').strip().replace('\\', '-').replace('.', '-').replace('/', '-')

        image_name =  image_dname + '.nii.gz'
        dump_image_path = os.path.join(output_folder, image_name)
        os.makedirs(os.path.dirname(dump_image_path), exist_ok=True)
        if not os.path.isdir(os.path.dirname(dump_image_path)):
            os.makedirs(os.path.dirname(dump_image_path))

        if method == 'sitk':
            sitk.WriteImage(image, dump_image_path)
        elif method == 'dcm2niix':
            tmp_folder = os.path.join(os.path.dirname(dump_image_path), 'tmp')
            output_filename = os.path.join(tmp_folder, 'correct_CT')
            if not os.path.isdir(tmp_folder):
                os.mkdir(tmp_folder)

            exec_filepath = os.path.join(os.path.dirname(__file__), "..", "MRIcroGL", "Resources", 'dcm2niix')
            try:
                subprocess.call(
                    ["{exec}".format(exec=exec_filepath),
                     "-o", "{output}".format(output=os.path.dirname(output_filename)),
                     "-f", "{filename}".format(filename=os.path.basename(output_filename)),
                     "-z", "y",
                     "{input}".format(input=os.path.dirname(reader.GetFileNames()[0]))])
            except Exception:
                if os.path.isdir(tmp_folder):
                    shutil.rmtree(tmp_folder)
                raise ValueError("DICOM to nifti conversion failed for folder: {}".format(input_folder))

            created_filename = None
            for _, _, files in os.walk(tmp_folder):
                for f in files:
                    if f.split('.')[-1] == 'gz':
                        created_filename = f
                break

            if created_filename is None:
                if os.path.isdir(tmp_folder):
                    shutil.rmtree(tmp_folder)
                return

            output_filename = os.path.join(tmp_folder, created_filename)
            #
            # if not os.path.exists(output_filename + '.nii.gz'):
            #     output_filename = output_filename + '_e1'
            #     if not os.path.exists(output_filename + '.nii.gz'):
            #         print('Could not find any reconverted CT for patient {}'.format(uid))
            #         continue

            # shutil.move(src=output_filename + '.nii.gz', dst=dump_image_path)
            shutil.move(src=output_filename, dst=dump_image_path)
            if os.path.isdir(tmp_folder):
                shutil.rmtree(tmp_folder)
        try:
            metatags_df.to_csv(dump_image_path.split('.')[0] + '_metadata.csv', index=False, encoding='utf-8')
        except Exception as e:
            # metatags = [[k, str.encode(reader.GetMetaData(0, k)).decode('utf8', 'surrogateescape')] for k in
            #             existing_dicom_keys]
            logging.warning(f"DICOM metadata tags with problematic encoding detected in: {input_folder} with {e}")
    except Exception as e:
        logging.error(f"Conversion failed for folder: {input_folder} failed with:\n {e}")