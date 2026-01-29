#!/usr/bin/env python3 

import pyrallis
from dataclasses import dataclass
from functools import partial

from os import path
import yaml
import numpy as np
from matplotlib import pyplot as plt
import multiprocessing as mp
import pandas as pd
import joblib

from utils import (
    get_mosaic_image_shape,
    merge_mosaic_images,
)
from tensorstore_utils import init_store, image_codecs

@dataclass
class Config:
    file_path : str = "testdata/shading_corrected.zarr"
    metadata_path : str = "testdata/metadata.yaml"
    positions_df_path: str = "testdata/mosaic_positions.csv"
    scene : str = '1.1%-50ms' #TODO change to int since the scene names may overlap
    stitch_every_t : int = 10
    try_ncc_thresholds = [0.1, 0.2, 0.3]

    output_path : str = "testdata/test_output"
    output_run_config_filename : str = "run_config.yaml"
    output_image_name : str = "stitched.zarr"
    
    num_cpus : int = mp.cpu_count()

def stitch_T(T, *, input_file_path, output_file_path, positions):
    input_image = init_store(input_file_path, mode="r") #In TMZYX order
    stitched = merge_mosaic_images(input_image[T,:,0].read().result(), positions)
    output_image = init_store(
        output_file_path, 
        mode="a"
    ) #In TZYX
    output_image[T].write(stitched).result()


def main():
    cfg = pyrallis.parse(Config)
    output_run_config_path = path.join(cfg.output_path, cfg.output_run_config_filename)
    with open(output_run_config_path, "w") as f:
        pyrallis.dump(cfg, f)
    
    input_image = init_store(cfg.file_path, mode="r") #In TMZYX order
    output_image_path = path.join(cfg.output_path, cfg.output_image_name)
    mosaic_image_shape, mosaic_positions = get_mosaic_image_shape(
        image_shape = input_image.shape[-2:],
        mosaic_positions = pd.read_csv(cfg.positions_df_path)[["y_pos","x_pos"]].values
    )
    print(f"Mosaic image shape: {mosaic_image_shape}")
    output_image_shape = (input_image.shape[0], input_image.shape[2], *mosaic_image_shape)
    output_image = init_store(
        output_image_path,
        shape=output_image_shape,
        dtype=input_image.dtype,
        codecs=image_codecs,
        mode="w"
    ) #In TZYX

    stitch_T_parallel = partial(
        stitch_T,
        input_file_path=cfg.file_path,
        output_file_path=output_image_path,
        positions=mosaic_positions
    )
    
    joblib.Parallel(n_jobs=cfg.num_cpus)(
        joblib.delayed(stitch_T_parallel)(T) for T in range(0, input_image.shape[0])
    )

    with open(cfg.metadata_path, "r") as f:
        metadata = yaml.safe_load(f)

    print(f"Image shape: {image.shape}")
    metadata = metadata[cfg.scene]
    if image.shape[2] > 1:
        raise ValueError("Currently only single Z slice images are supported.")


    output_image_zarr = init_store(output_image_path, mode="a")
    output
    
    
if __name__ == "__main__":
    main()