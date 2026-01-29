#!/usr/bin/env python3 

import pyrallis
from dataclasses import dataclass
from functools import partial

from os import path
import multiprocessing as mp
import pandas as pd
import joblib
from matplotlib import pyplot as plt
import numpy as np

from utils import (
    get_mosaic_image_shape,
    merge_mosaic_images,
)
from tensorstore_utils import init_store, codecs_image

@dataclass
class Config:
    file_path : str = "testdata/shading_corrected.zarr"
    positions_df_path: str = "testdata/mosaic_positions.csv"

    output_path : str = "testdata/test_output"
    output_run_config_filename : str = "run_config.yaml"
    output_image_name : str = "stitched.zarr"
    output_test_image_name : str = "test_stitched_export_image.png"
    
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
    
    input_image = init_store(path.abspath(cfg.file_path), mode="r") #In TMZYX order

    output_image_path = path.abspath(path.join(cfg.output_path, cfg.output_image_name))
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
        codecs=codecs_image,
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
    
    plt.figure(figsize=(10,10))
    im = output_image[0,0].read().result()
    qs = np.quantile(im, [0.01,0.99])
    plt.imshow(im,vmin=qs[0],vmax=qs[1])
    plt.colorbar()
    output_test_image_path = path.join(cfg.output_path, cfg.output_test_image_name)
    plt.savefig(output_test_image_path, dpi=300, bbox_inches='tight')
    print(f"Saved test stitched image to {output_test_image_path}")
    
    
if __name__ == "__main__":
    main()