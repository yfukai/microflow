#!/usr/bin/env python3 

import pyrallis
from dataclasses import dataclass, field
from functools import partial

from os import path
from glob import glob
import multiprocessing as mp
import pandas as pd
import joblib
import yaml
from matplotlib import pyplot as plt
import numpy as np

from utils import (
    get_mosaic_image_shape,
    merge_mosaic_images,
)
from tensorstore_utils import init_store, codecs_image

@dataclass
class Config:
    file_path_pattern : str = "testdata/shading_corrected*.zarr"
    scene : str = '1.1%-50ms' #TODO change to int since the scene names may overlap
    channels: list[tuple[int,str]] = field(default_factory=lambda: [(0,"Channel_0")])
    metadata_path : str = "testdata/test_metadata.yaml"
    positions_df_path: str = "testdata/mosaic_positions.csv"

    output_path : str = "testdata/test_output"
    output_run_config_filename : str = "run_config.yaml"
    output_image_name : str = "stitched.zarr"
    output_test_image_name : str = "test_stitched_export_image.png"
    
    num_cpus : int = mp.cpu_count()



def main():
    cfg = pyrallis.parse(Config)
    output_run_config_path = path.join(cfg.output_path, cfg.output_run_config_filename)
    with open(output_run_config_path, "w") as f:
        pyrallis.dump(cfg, f)
    
    image_paths = sorted(glob(cfg.file_path_pattern))
    input_image = init_store(path.abspath(image_paths[0]), mode="r") #In TMZYX order
    with open(cfg.metadata_path, "r") as f:
        metadata = yaml.safe_load(f)
    metadata = metadata[cfg.scene]

    output_image_path = path.abspath(path.join(cfg.output_path, cfg.output_image_name))
    mosaic_image_shape, mosaic_positions = get_mosaic_image_shape(
        image_shape = input_image.shape[-2:],
        mosaic_positions = pd.read_csv(cfg.positions_df_path)[["y_pos","x_pos"]].values
    )
    print(f"Mosaic image shape: {mosaic_image_shape}")

    output_image_shape = (input_image.shape[0], len(cfg.channels), input_image.shape[2], *mosaic_image_shape) #In TCZYX
    output_image = init_store(
        output_image_path,
        shape=output_image_shape,
        dtype=input_image.dtype,
        codecs=codecs_image,
        mode="w"
    ) #In TCZYX
    print("Initialized output stitched image store. Shape:", output_image.shape)

    cfg_channels = sorted(cfg.channels, key=lambda x:x[0])
    meta_channels = metadata["channel_names"]
    if not len(cfg_channels) == len(meta_channels):
        raise ValueError(f"Number of channels in config {len(cfg.channels)} does not match number of channels in metadata {len(metadata['channel_names'])}")
    if not all(cfg_channels[i][1] == meta_channels[cfg_channels[i][0]] for i in range(len(cfg_channels))):
        raise ValueError(f"Channel indices and names {cfg.channels} do not match metadata channel names {metadata['channel_names']}")

    channel_index_map = {i:c[0] for i,c in enumerate(cfg.channels)}

    def stitch_T(T, C):
        input_file_path = path.abspath(image_paths[C])
        input_image = init_store(input_file_path, mode="r") #In TMZYX order
        stitched = merge_mosaic_images(input_image[T,:,0].read().result(), mosaic_positions)
        output_image = init_store(
            output_image_path,
            mode="a"
        ) #In TZYX
        output_image[T, channel_index_map[C]].write(stitched).result()

    
    joblib.Parallel(n_jobs=cfg.num_cpus)(
        joblib.delayed(stitch_T)(T,C) for C in range(len(cfg.channels)) for T in range(input_image.shape[0])
    )
    
    plt.figure(figsize=(10,10))
    im = output_image[0,0,0].read().result()
    qs = np.quantile(im, [0.01,0.99])
    plt.imshow(im,vmin=qs[0],vmax=qs[1])
    plt.colorbar()
    output_test_image_path = path.join(cfg.output_path, cfg.output_test_image_name)
    plt.savefig(output_test_image_path, dpi=300, bbox_inches='tight')
    print(f"Saved test stitched image to {output_test_image_path}")
    
    
if __name__ == "__main__":
    main()