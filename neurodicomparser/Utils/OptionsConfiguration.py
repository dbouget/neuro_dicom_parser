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
        self.domain_target = "neuro"
        self.scope = "patient"
        self.dicom_structure = "sectra_cdmedia"
        self.dicom_conversion_method = "dcm2niix"
        self.dicom_fully_anonymised = False
        self.override = False
        self.config_fn = None
        self.user_options = None
        self.identification_domain = "neuro"
        self.identification_status = True

    def __parse_user_options(self):
        cf_key = "Case"
        if self.user_options.has_option(cf_key, 'input_folder'):
            if self.user_options[cf_key]['input_folder'].split('#')[0].strip() != '':
                self.input_folder = self.user_options[cf_key]['input_folder'].split('#')[0].strip()

        if self.user_options.has_option(cf_key, 'output_folder'):
            if self.user_options[cf_key]['output_folder'].split('#')[0].strip() != '':
                self.output_folder = self.user_options[cf_key]['output_folder'].split('#')[0].strip()

        cf_key = "Default"
        if self.user_options.has_option(cf_key, 'domain'):
            if self.user_options[cf_key]['domain'].split('#')[0].strip() != '':
                self.domain_target = self.user_options[cf_key]['domain'].split('#')[0].strip().lower()
        if self.domain_target not in ["neuro", "mediastinum"]:
            raise ValueError(f"The domain with value {self.domain_target} is not handled!"
                             f"Please select from [neuro, mediastinum]!")

        if self.user_options.has_option(cf_key, 'scope'):
            if self.user_options[cf_key]['scope'].split('#')[0].strip() != '':
                self.scope = self.user_options[cf_key]['scope'].split('#')[0].strip().lower()
        if self.scope not in ["cohort", "patient", "timepoint", "image"]:
            raise ValueError(f"The scope with value {self.scope} is not handled! "
                             f"Please select from [cohort, patient, timepoint, image]!")

        if self.user_options.has_option(cf_key, 'override_existing'):
            if self.user_options[cf_key]['override_existing'].split('#')[0].strip() != '':
                self.override = True if self.user_options[cf_key]['override_existing'].split('#')[0].strip().lower() == "true" else False

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