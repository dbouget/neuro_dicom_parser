FROM python:3.10-slim

MAINTAINER David Bouget <david.bouget@sintef.no>

ENV LANG=C.UTF-8 LC_ALL=C.UTF-8

RUN apt-get update -y
RUN apt-get upgrade -y
RUN apt-get -y install sudo
RUN apt-get update && apt-get install -y git

WORKDIR /workspace

RUN git clone https://github.com/dbouget/neuro_dicom_parser.git
RUN pip3 install --upgrade pip
RUN pip3 install -e neuro_dicom_parser

RUN mkdir /workspace/resources

# Download and place resources
RUN python /workspace/neuro_dicom_parser/Utils/ensure_dcm2nii_present.py
RUN python /workspace/neuro_dicom_parser/Utils/ensure_models_present.py

ENTRYPOINT ["python3","/workspace/neuro_dicom_parser/main.py"]