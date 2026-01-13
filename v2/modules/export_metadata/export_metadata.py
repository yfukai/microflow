import pyrallis
from dataclasses import dataclass

from bioio import BioImage
import os
from os import path
import io
import contextlib
import yaml
from datetime import timedelta
from dateutil import parser
import numpy as np
from matplotlib import pyplot as plt

@dataclass
class Config:
    """ Training config for Machine Learning """
    file_path : str = "../testdata/test3.nd2"
    output_metadata_path : str = "../testdata/test3_output/test3_metadata.yaml"
    output_test_image_path : str = "../testdata/test3_output/test3_test_image.png"

def main(cfg: Config):
    print(f"File Path: {cfg.file_path}")
    print(f"Output Metadata Path: {cfg.output_metadata_path}")
    print(f"Output Test Image Path: {cfg.output_test_image_path}")


