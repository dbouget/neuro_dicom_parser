import configparser
import logging
import os
import sys
import platform
import datetime
import time
from pathlib import PurePath


class OptionsConfiguration:
    """
    Singleton class to have access from anywhere in the code at the various paths and configuration parameters.
    """
    __instance = None

    @staticmethod
    def getInstance():
        """ Static access method. """
        if OptionsConfiguration.__instance == None:
            OptionsConfiguration()
        return OptionsConfiguration.__instance

    def __init__(self):
        """ Virtually private constructor. """
        if OptionsConfiguration.__instance != None:
            raise Exception("This class is a singleton!")
        else:
            OptionsConfiguration.__instance = self
            self.__setup()

    def __setup(self):
        """
        Definition of all attributes accessible through this singleton.
        """
        self.__reset()

    def __reset(self) -> None:
        self.input_folder = None
        self.output_folder = None
        self.content_granularity = "patient"
        self.dicom_structure = "sectra_cdmedia"
        self.dicom_conversion_method = "dcm2niix"
        self.dicom_fully_anonymised = False
        self.dicom_override_existing = False
        self.config_fn = None
        self.user_options = None
        self.identification_domain = "neuro"
        self.identification_status = True
        self.identification_override_classification = False
        self.identification_override_selection = False

    def __parse_user_options(self):
        cf_key = "Case"
        if self.user_options.has_option(cf_key, 'input_folder'):
            if self.user_options[cf_key]['input_folder'].split('#')[0].strip() != '':
                self.input_folder = self.user_options[cf_key]['input_folder'].split('#')[0].strip()

        if self.user_options.has_option(cf_key, 'output_folder'):
            if self.user_options[cf_key]['output_folder'].split('#')[0].strip() != '':
                self.output_folder = self.user_options[cf_key]['output_folder'].split('#')[0].strip()

        if self.user_options.has_option(cf_key, 'content_granularity'):
            if self.user_options[cf_key]['content_granularity'].split('#')[0].strip() != '':
                self.content_granularity = self.user_options[cf_key]['content_granularity'].split('#')[0].strip().lower()
        if self.content_granularity not in ["cohort", "patient", "timepoint", "image"]:
            raise ValueError(f"The content granularity with value {self.content_granularity} is not handled! "
                             f"Please select from [cohort, patient, timepoint, image]!")

        cf_key = "DICOM"
        if self.user_options.has_option(cf_key, 'structure'):
            if self.user_options[cf_key]['structure'].split('#')[0].strip() != '':
                self.dicom_structure = self.user_options[cf_key]['structure'].split('#')[0].strip().lower()
        if self.dicom_structure not in ["sectra_cdmedia", "manual"]:
            raise ValueError(f"The DICOM structure with value {self.dicom_structure} is not handled!"
                             f"Please select from [sectra_cdmedia, manual]!")
        if self.user_options.has_option(cf_key, 'conversion_method'):
            if self.user_options[cf_key]['conversion_method'].split('#')[0].strip() != '':
                self.dicom_conversion_method = self.user_options[cf_key]['conversion_method'].split('#')[0].strip().lower()
        if self.dicom_conversion_method not in ["dcm2niix", "sitk"]:
            raise ValueError(f"The DICOM conversion method with value {self.dicom_structure} is not handled!"
                             f"Please select from [dcm2niix, sitk]!")
        if self.user_options.has_option(cf_key, 'fully_anonymised'):
            if self.user_options[cf_key]['fully_anonymised'].split('#')[0].strip() != '':
                self.dicom_fully_anonymised = True if self.user_options[cf_key]['fully_anonymised'].split('#')[0].strip().lower() == "true" else False
                
        if self.user_options.has_option(cf_key, 'override_existing'):
            if self.user_options[cf_key]['override_existing'].split('#')[0].strip() != '':
                self.dicom_override_existing = True if self.user_options[cf_key]['override_existing'].split('#')[0].strip().lower() == "true" else False

        cf_key = "Identification"
        if self.user_options.has_option(cf_key, 'domain'):
            if self.user_options[cf_key]['domain'].split('#')[0].strip() != '':
                self.identification_domain = self.user_options[cf_key]['domain'].split('#')[0].strip().lower()
        if self.identification_domain not in ["neuro", "mediastinum"]:
            raise ValueError(f"The domain with value {self.identification_domain} is not handled!"
                             f"Please select from [neuro, mediastinum]!")
        if self.user_options.has_option(cf_key, 'perform'):
            if self.user_options[cf_key]['perform'].split('#')[0].strip() != '':
                self.identification_status = True if self.user_options[cf_key]['perform'].split('#')[0].strip().lower() == "true" else False

        if self.user_options.has_option(cf_key, 'override_classification'):
            if self.user_options[cf_key]['override_classification'].split('#')[0].strip() != '':
                self.identification_override_classification = True if self.user_options[cf_key]['override_classification'].split('#')[0].strip().lower() == "true" else False
     
        if self.user_options.has_option(cf_key, 'override_selection'):
            if self.user_options[cf_key]['override_selection'].split('#')[0].strip() != '':
                self.identification_override_selection = True if self.user_options[cf_key]['override_selection'].split('#')[0].strip().lower() == "true" else False

    def init(self, config_fn: str) -> None:
        try:
            self.config_fn = config_fn
            if not self.config_fn:
                self.config_fn = os.path.join(os.path.dirname(__file__), '..', 'user_options.ini')
            if not os.path.exists(self.config_fn):
                raise ValueError(
                    f"A configuration is necessary either as input through -c or directly at the folder root.")

            self.user_options = configparser.ConfigParser()
            self.user_options.read(self.config_fn)
            self.__parse_user_options()
        except Exception as e:
            logging.error(f"User options file could not be read and has been ignored, collected {e}")