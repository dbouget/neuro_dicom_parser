import shutil
import os
import traceback
import json
import subprocess
import configparser
import pandas as pd
import numpy as np
from raidionicsrads.compute import run_rads


def compute_classification(input_filename: str, target_name: str, override: bool = False) -> None:
    """
    Generic method for running classification on an input image.

    :param input_filename:
    :param target_name:
    :param override:
    :return:
    """
    model_name = None
    if target_name == "sequence":
        model_name = "MRI_SequenceClassifier"
    else:
        print(f"No classification model for {target_name}")
        return

    dest_classification_file = input_filename.replace('.nii.gz', '_sequence_classification_results.csv')
    # The cases for a recompute are: (i) override, (ii) new database entry, (iii) filepath is None, (iv) filepath cannot be found on disk.
    if override or not os.path.exists(dest_classification_file):
        tmp_folder = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'tmp')
        if os.path.exists(tmp_folder):
            shutil.rmtree(tmp_folder)
        output_prefix = os.path.join(tmp_folder, 'segmentation')
        if not os.path.isdir(tmp_folder):
            os.mkdir(tmp_folder)

        surrogate_folder_path = os.path.join(tmp_folder, 'pipeline_input')
        try:
            if os.path.exists(surrogate_folder_path):
                # Should not happen as we should try/except around the processing and delete it there always.
                shutil.rmtree(surrogate_folder_path)

            os.makedirs(surrogate_folder_path)
            preop_folder = os.path.join(surrogate_folder_path, "T0")
            os.makedirs(preop_folder)
            shutil.copyfile(src=input_filename, dst=os.path.join(preop_folder, os.path.basename(input_filename)))

            # Setting up the runtime configuration file, mandatory for the raidionics_rads_lib to run.
            rads_config = configparser.ConfigParser()
            rads_config.add_section('Default')
            rads_config.set('Default', 'task', 'neuro_diagnosis')
            rads_config.set('Default', 'caller', '')
            rads_config.add_section('System')
            rads_config.set('System', 'gpu_id', "-1")  # Always running on CPU
            rads_config.set('System', 'input_folder', surrogate_folder_path)
            rads_config.set('System', 'output_folder', tmp_folder)
            rads_config.set('System', 'model_folder', os.path.join(os.path.dirname(__file__), "..", "Models"))
            pipeline_filename = os.path.join(tmp_folder, 'rads_pipeline.json')
            # Option1. Copying directly from the model folder
            # shutil.copyfile(src=os.path.join(SharedResources.getInstance().raidionics_models_root, model_name, 'pipeline.json'),
            #                 dst=pipeline_filename)
            # Option2. Hard-coding for the different use cases.
            # Actually mandatory in the case of MRI_Brain where the pipeline must be adjusted on the fly to run on multiple sequences...
            pipeline = create_classification_pipeline(model_name)
            with open(pipeline_filename, 'w', newline='\n') as outfile:
                json.dump(pipeline, outfile, indent=4)
            rads_config.set('System', 'pipeline_filename', pipeline_filename)
            rads_config.add_section('Runtime')
            rads_config.set('Runtime', 'reconstruction_method', 'probabilities')
            rads_config.set('Runtime', 'reconstruction_order', 'resample_first')
            rads_config_filename = os.path.join(tmp_folder, 'rads_config.ini')
            with open(rads_config_filename, 'w') as outfile:
                rads_config.write(outfile)
        except Exception as e:
            print(f"Classification external setup failed with {e}.")
            return

        print(f"Start automatic classification in {input_filename}.")
        try:
            run_rads(config_filename=rads_config_filename)
        except Exception:
            print(traceback.format_exc())
            raise ValueError(f"Automatic classification failed on: {input_filename}")

        results_filename = os.path.join(tmp_folder, "MRSequence_classification_results_raw.csv")
        if not os.path.exists(results_filename):
            raise ValueError(f"Automatic classification failed, no results file on disk.")
        results_df = pd.read_csv(results_filename)
        max_ind = np.argmax(results_df["Prediction"])
        output_image_filename = input_filename.replace('.nii.gz', '_' + results_df["Class"].values[max_ind] + '_' + str(int(results_df["Prediction"].values[max_ind] * 100.)) + '.nii.gz')
        shutil.move(src=input_filename, dst=output_image_filename)
        shutil.move(src=input_filename.replace('.nii.gz', '_metadata.csv'), dst=output_image_filename.replace('.nii.gz', '_metadata.csv'))
        shutil.copyfile(src=results_filename, dst=dest_classification_file)

def create_classification_pipeline(model_name: str) -> dict:
    """

    """
    model_target = None
    if model_name == "MRI_SequenceClassifier":
        model_target = ["MRSequence"]
    else:
        pass

    pip = {}
    pip_num_int = 0

    pip_num_int = pip_num_int + 1
    pip_num = str(pip_num_int)
    pip[pip_num] = {}
    pip[pip_num]["task"] = 'Classification'
    pip[pip_num]["inputs"] = {}
    pip[pip_num]["target"] = model_target
    pip[pip_num]["model"] = model_name
    pip[pip_num]["description"] = model_name.split('_')[1] + " classification"

    return pip