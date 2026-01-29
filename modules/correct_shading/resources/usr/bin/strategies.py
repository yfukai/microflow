from enum import Enum
from dataclasses import dataclass
import numpy as np
from skimage import transform, filters, morphology

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
        return {"background": bg.astype(np.float32)}

    def correct(self, image_data: np.ndarray, profiles: dict[str, np.ndarray]) -> np.ndarray:
        profile = profiles["background"]
        corrected = image_data.astype(np.float32) - profile
        return corrected
