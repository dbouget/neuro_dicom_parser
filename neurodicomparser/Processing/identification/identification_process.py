from ...Utils.OptionsConfiguration import *
from ...Processing.identification.mri_sequence_processing import identify_sequences, sequence_selection
from ...Processing.identification.ct_sequence_processing import ct_sequence_selection

def identification_process(input_folder: str):
    try:
        override_classification = OptionsConfiguration.getInstance().identification_override_classification
        override_selection = OptionsConfiguration.getInstance().identification_override_selection
        if not OptionsConfiguration.getInstance().identification_status:
            return 
        
        if OptionsConfiguration.getInstance().identification_domain == "neuro":
            identify_sequences(input_folder=input_folder, override=override_classification)
            sequence_selection(input_folder=input_folder, override=override_selection)
        elif OptionsConfiguration.getInstance().identification_domain == "mediastinum":
            ct_sequence_selection(input_folder=input_folder, override=override_selection)
    except Exception as e:
        raise ValueError(f"Identification process failed with {e}")