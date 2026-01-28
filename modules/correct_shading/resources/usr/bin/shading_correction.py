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
from dask import array as da
from skimage import transform, filters, morphology
import multiprocessing as mp

class PerImageStrategyKind(str, Enum):
    none = "none"
    imodpoly = "imodpoly"
    local_subtraction = "local_subtraction"

class PerImageStrategyConfig:
    strategy: PerImageStrategyKind
    
    def estimate(self, image_data: np.ndarray) -> np.ndarray:
        """Estimate the additive background profile from the given image data.

        Parameters
        ----------
        image_data : np.ndarray
            The image data to estimate the background from. The shape is expected to be (Z, Y, X).

        Returns
        -------
        np.ndarray
            The estimated background profile.

        Raises
        ------
        NotImplementedError
            If the estimation strategy is not implemented.
        """
        raise NotImplementedError



@dataclass
class NullImageStrategyConfig(PerImageStrategyConfig):
    strategy: PerImageStrategyKind = PerImageStrategyKind.none


@dataclass
class ImodpolyConfig(PerImageStrategyConfig):
    strategy: PerImageStrategyKind = PerImageStrategyKind.imodpoly
    poly_order: int = 2
    tol: float = 1e-3
    max_iter: int = 200
    num_std: float = 1.0

def scaled_filter(im2d,scale,fn,anti_aliasing=True):
    """ apply filter for scaled image and resize to original size """
    shape = im2d.shape
    im2d = np.array(im2d, dtype=np.float32)
    im2d = transform.rescale(im2d, 
        scale,
        anti_aliasing=anti_aliasing,
        preserve_range=True)
    im2d = fn(im2d)
    return transform.resize(im2d,shape, preserve_range=True)

def local_subtraction_2d_ignore_zero(im2d, scaling=0.1, median_disk_size=4):
    if scaling <= 0 or scaling >= 1:
        raise ValueError("scaling must be between 0 and 1")
    if im2d.ndim != 2:
        raise ValueError("im2d must be a 2D array")
    def median_filter(im):
        return filters.median(
                    im,morphology.disk(median_disk_size)
                )
    if np.count_nonzero(im2d) == 0:
        return im2d
    return scaled_filter(im2d, scaling, median_filter, anti_aliasing=True)

@dataclass
class LocalSubtractionConfig:
    strategy: PerImageStrategyKind = PerImageStrategyKind.local_subtraction
    scaling: float = 0.1
    median_disk_size: int = 4

    def estimate(self, image_data: np.ndarray) -> np.ndarray:
        return np.array([local_subtraction_2d_ignore_zero(im, 
                                                scaling=self.scaling,
                                                median_disk_size=self.median_disk_size)
                         for im in image_data])

class PerFrameStrategyKind(str, Enum):
    percentile = "percentile"
    none = "none"

class PerFrameStrategyConfig:
    strategy: PerFrameStrategyKind
    def estimate(self, image_data: np.ndarray) -> dict[str, np.ndarray]:
        raise NotImplementedError

    def correct(self, image_data: np.ndarray, profiles: dict[str, np.ndarray]) -> np.ndarray:
        raise NotImplementedError

@dataclass
class NullFrameStrategyConfig(PerFrameStrategyConfig):
    strategy: PerFrameStrategyKind = PerFrameStrategyKind.none

    def estimate(self, image_data: np.ndarray) -> dict[str, np.ndarray]:
        raise NotImplementedError

    def correct(self, image_data: np.ndarray, profiles: dict[str, np.ndarray]) -> np.ndarray:
        raise NotImplementedError

@dataclass
class PercentileConfig(PerFrameStrategyConfig):
    strategy: PerFrameStrategyKind = PerFrameStrategyKind.percentile
    percentile: float = 50.0
    robust: bool = False
    deviation_factor: float = 2.0
    smoothing_sigma: float = 0.0

    def estimate(self, image_data: np.ndarray) -> dict[str, np.ndarray]:
        if self.robust:
            deviation = np.abs(np.median(image_data, axis=0, keepdims=True) - image_data)
            median_deviation = np.median(deviation, axis=0)
            image_data = np.where(deviation < median_deviation * self.deviation_factor, 
                                  image_data, np.nan)
            bg = np.nanpercentile(image_data, self.percentile, axis=0, keepdims=True)
        else:
            bg = np.percentile(image_data, self.percentile, axis=0, keepdims=True)
        if self.smoothing_sigma > 0:
            bg = filters.gaussian(bg, sigma=self.smoothing_sigma, preserve_range=True)
        return {"background": bg}

    def correct(self, image_data: np.ndarray, profiles: dict[str, np.ndarray]) -> np.ndarray:
        profile = profiles["background"]
        corrected = image_data - profile
        return corrected

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
    output_test_image_filename_prefix : str = "background"
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
        raise NotImplementedError("Only Z=1 is supported currently.")
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


    
# %%
def main():
    cfg = pyrallis.parse(config_class=Config)
   
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
#    mosaic_dim = metadata["mosaic_dimension"]
#    image_data = read_mosaic_image(image, mosaic_dim, "TZYX", C=cfg.channel_index)
#
#    print(f"Metadata: {metadata}")
#    print(f"Image data shape: {image_data.shape}")

if __name__ == '__main__':
    main()

# %%
    
#cfg = pyrallis.parse(config_class=Config)
cfg = Config()
cfg.channel_index=0
cfg.per_frame_strategy.smoothing_sigma=10.0
cfg.per_image_strategy = LocalSubtractionConfig(scaling=0.1, median_disk_size=4)

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

# %%
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
# %%
test_image = image_data[:,0].compute()  # First timepoint

# %%

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
fig.savefig(path.join(cfg.output_path, cfg.output_run_config_filename)
# %%

with mp.Pool(processes=cfg.num_cpus) as pool:
    corrected_frames = pool.starmap(process_frame, [(image_data[t].compute(), cfg) for t in range(image_data.shape[0])])

# Parallelly process all frames
corrected_zarr = da.map_blocks(
    lambda block: process_frame(block, cfg=cfg)[0],
    image_data,
    dtype=image_data.dtype,
    chunks=image_data.chunks
)


# %%
corrected_zarr.shape  # (T, M, Z, Y, X)
# %%
image_data.shape
# %%
image_data.chunks
# %%
corrected = corrected_zarr.compute()
# %%
