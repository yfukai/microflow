import pyrallis
from dataclasses import dataclass

from bioio import BioImage
import os
from os import path
import yaml
import numpy as np
from matplotlib import pyplot as plt
from utils import read_mosaic_image

@dataclass
class Config:
    file_path : str = "testdata/test.czi"
    metadata_path : str = "testdata/metadata.yaml"
    channel_index : int = 0
    strategy : str = "percentile" # options: "percentile", "mean", "pybaselines"
    percentile_percentile : float = 50.0
    pybaselines_method : str = 
    output_path : str = "testdata/test_output"
    output_correction_data_filename_prefix : str = "shading_correction"
    output_test_image_filename_prefix : str = "background"

def main():
    cfg = pyrallis.parse(config_class=Config)
    print(f"File Path: {cfg.file_path}")
    print(f"Metadata Path: {cfg.metadata_path}")

    image = BioImage(cfg.file_path, 
                     reconstruct_mosaic=False, 
                     use_aicspylibczi=True)
    with open(cfg.metadata_path, 'r') as f:
        metadata = yaml.safe_load(f)
    mosaic_dim = metadata["mosaic_dimension"]
    image_data = read_mosaic_image(image, mosaic_dim, "TZYX", C=cfg.channel_index)

    print(f"Metadata: {metadata}")
    print(f"Image data shape: {image_data.shape}")


if __name__ == '__main__':
    main()