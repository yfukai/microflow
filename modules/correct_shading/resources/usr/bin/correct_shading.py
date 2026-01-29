# %%
import pyrallis
from dataclasses import dataclass, field
from enum import Enum
from typing import Union

from bioio import BioImage
from os import path
import yaml
import numpy as np
from matplotlib import pyplot as plt
from utils import read_mosaic_image
import dask
from dask import array as da
import multiprocessing as mp
from shutil import rmtree

from tensorstore_utils import init_store, codecs_image
from strategies import (
    PerImageStrategyConfig,
    PerImageStrategyKind,
    NullImageStrategyConfig,
    PerFrameStrategyConfig,
    PerFrameStrategyKind,
    PercentileConfig,
)


@dataclass
class Config:
    file_path : str = "testdata/test.czi"
    metadata_path : str = "testdata/test_metadata.yaml"
    scene : Union[str,int] = 0
    channel_index : int = 0

    preprocessing_for_per_frame_estimation : PerImageStrategyConfig = field(default_factory=NullImageStrategyConfig)
    per_frame_strategy : PerFrameStrategyConfig = field(default_factory=PercentileConfig)
    per_image_strategy : PerImageStrategyConfig = field(default_factory=NullImageStrategyConfig)

    output_path : str = "testdata/test_output"
    output_run_config_filename : str = "run_config.yaml"
    output_correction_data_filename_prefix : str = "shading_correction"
    output_test_image_filename : str = "shading_correction_result.png"
    output_image_name : str = "corrected_image.zarr"
    
    num_cpus : int = mp.cpu_count()
    

    
def process_frame(frame_data: np.ndarray, *, cfg: Config) -> tuple[np.ndarray, dict[str, np.ndarray], np.ndarray|None]:
    """Process a single frame with shading correction.

    Parameters
    ----------
    frame_data : np.ndarray
        Input frame data to be corrected. Expects shape (M, Z, Y, X) or (1, Z, Y, X).
        Currently, only Z=1 is supported.
    cfg : Config
        Configuration object containing correction settings.

    Returns
    -------
    np.ndarray
        Corrected frame data. Same shape as input.
    dict[str, np.ndarray]
        Estimated profiles used for correction.
    np.ndarray | None
        Estimated image-level profile, if applicable; otherwise, None.
    """
    if frame_data.shape[1] != 1:
        raise NotImplementedError(f"Only Z=1 is supported currently. {frame_data.shape} found.")
    if frame_data.ndim != 4:
        raise ValueError("frame_data must be a 4D array with shape (M, Z, Y, X).")

    if cfg.preprocessing_for_per_frame_estimation.strategy != PerImageStrategyKind.none:
        per_frame_estimation_preprocessed = np.array([
            cfg.preprocessing_for_per_frame_estimation.estimate(frame_data[m])
            for m in range(frame_data.shape[0])
        ])
    else:
        per_frame_estimation_preprocessed = frame_data

    if cfg.per_frame_strategy.strategy != PerFrameStrategyKind.none:
        frame_profile = cfg.per_frame_strategy.estimate(per_frame_estimation_preprocessed)
        frame_data = cfg.per_frame_strategy.correct(frame_data, frame_profile)
    else:
        frame_profile = {}
        frame_data = frame_data
    if cfg.per_image_strategy.strategy != PerImageStrategyKind.none:
        image_profile = np.array([cfg.per_image_strategy.estimate(im) for im in frame_data])
        frame_data = frame_data - image_profile
    else:
        image_profile = None
        frame_data = frame_data
    return frame_data, frame_profile, image_profile[0] if image_profile is not None else None


def dask_block_index_to_slices(block_index, chunks):
    # chunks: x.chunks (tuple of tuples)
    out = []
    for i, c in zip(block_index, chunks):
        start = sum(c[:i])
        stop  = start + c[i]
        out.append(slice(start, stop))
    return tuple(out)


def main():
    cfg = pyrallis.parse(Config)
    print("Shading correction with the following configuration:")
    print(cfg)
    print(f"File Path: {cfg.file_path}")
    print(f"Metadata Path: {cfg.metadata_path}")
    output_run_config_path = path.join(cfg.output_path, cfg.output_run_config_filename)
    with open(output_run_config_path, "w") as f:
        pyrallis.dump(cfg, f)

    image = BioImage(cfg.file_path, 
                     reconstruct_mosaic=False, 
                     use_aicspylibczi=True)
    with open(cfg.metadata_path, 'r') as f:
        metadata = yaml.safe_load(f)

    if isinstance(cfg.scene, int):
        scene_name = image.scenes[cfg.scene]
    else:
        scene_name = cfg.scene
    print(f"Using scene: {scene_name}")
    mosaic_dim = metadata[scene_name]["mosaic_dimension"]
    image_data = read_mosaic_image(image, mosaic_dim, "TZYX", C=cfg.channel_index)
    # image_data : "MTZYX"
    print(f"Metadata: {metadata}")
    print(f"Image data shape: {image_data.shape}")
    print(f"Image data chunks: {image_data.chunks}")

    ################ Process and visualize a test image ################
    test_image = image_data[:,0].compute()  # First timepoint
    corrected, frame_profile, image_profile_first = process_frame(test_image, cfg=cfg)

    print(f"Estimated profile keys: {list(frame_profile.keys())}")
    ncols = 2+len(frame_profile)+ (1 if image_profile_first is not None else 0)
    fig, axes = plt.subplots(1,ncols, 
                             figsize=(5*ncols,5))
    sm = axes[0].imshow(image_data[0,0,0], cmap='gray')
    fig.colorbar(sm, ax=axes[0])
    axes[0].set_title("Original Image")
    sm = axes[1].imshow(corrected[0,0], cmap='gray')
    fig.colorbar(sm, ax=axes[1])
    axes[1].set_title("Corrected Image")
    for jj, (key, prof) in enumerate(frame_profile.items()):
        sm = axes[2+jj].imshow(prof[0,0], cmap='gray')
        fig.colorbar(sm, ax=axes[2+jj])
        axes[2+jj].set_title(f"Profile: {key}")
    for ax in axes:
        ax.axis('off')
    if image_profile_first is not None:
        sm = axes[-1].imshow(image_profile_first[0], cmap='gray')
        fig.colorbar(sm, ax=axes[-1])
        axes[-1].set_title("Image-level Profile")
    fig.tight_layout()
    fig.show()
    fig.savefig(path.join(cfg.output_path, cfg.output_test_image_filename), bbox_inches='tight')
    
    ################ Analyze all frames and write output zarr ################
    output_zarr_path = path.join(cfg.output_path, cfg.output_image_name)
    rmtree(output_zarr_path, ignore_errors=True)
    print(f"Writing corrected image to: {output_zarr_path}")

    image_data_rechunked = da.moveaxis(image_data, 0, 1).rechunk({0:1, 1:-1, 2:-1, 3:-1, 4:-1})

    store_args = dict(
        path=output_zarr_path,
        dtype=np.float32,
        shape=image_data_rechunked.shape,
        chunks=(1,1)+image_data_rechunked.shape[2:],
        mode="a",
        codecs=codecs_image,
    )

    @dask.delayed
    def compute_and_write(chunk, slices):
        print(f"Processing chunk with slices: {slices}")
        print(chunk.shape)
        corrected_chunk, _, _ = process_frame(chunk[0], cfg=cfg)
        output_store = init_store(**store_args)
        output_store[slices].write(corrected_chunk.astype(np.float32)[np.newaxis]).result()
        print(f"Processed and wrote chunk at location {slices}")
        return corrected_chunk

    tasks = []
    delayed_array = image_data_rechunked.to_delayed()
    for block_index in np.ndindex(*image_data_rechunked.numblocks):
        d = delayed_array[block_index] 
        slc = dask_block_index_to_slices(block_index, image_data_rechunked.chunks)
        tasks.append(compute_and_write(d, slc))

    dask.compute(*tasks)

if __name__ == '__main__':
    main()


