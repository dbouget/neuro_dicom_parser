from ...Utils.OptionsConfiguration import *
from ...Processing.identification.mri_sequence_processing import identify_sequences, sequence_selection
from ...Processing.identification.ct_sequence_processing import ct_sequence_selection

def identification_process(input_folder: str):
    try:
        if not OptionsConfiguration.getInstance().identification_status:
            return 
        
        if OptionsConfiguration.getInstance().identification_domain == "neuro":
            identify_sequences(input_folder=input_folder)
            sequence_selection(input_folder=input_folder)
        elif OptionsConfiguration.getInstance().identification_domain == "mediastinum":
            ct_sequence_selection(input_folder=input_folder)
    except Exception as e:
        raise ValueError(f"Identification process failed with {e}")