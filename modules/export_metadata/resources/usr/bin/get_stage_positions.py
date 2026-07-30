import numpy as np
import nd2
from bioio import BioImage

# Signs converting the (Y, X) stage coordinates in microns into the (Y, X) image
# coordinates in pixels: the image Y axis follows the stage Y axis, while the image
# X axis runs opposite to the stage X axis. Determined by maximizing the normalized
# cross correlation of the overlapping regions of neighboring tiles.
ND2_STAGE_TO_IMAGE_SIGNS = np.array([1.0, -1.0])


def _nd2_stage_positions_um(file_path: str) -> np.ndarray:
    """Return the (Y, X) stage positions of the points of an ND2 file, in microns.

    Parameters
    ----------
    file_path : str
        Path to the ND2 file.

    Returns
    -------
    np.ndarray
        Stage positions in microns, in the order of the acquired points.
    """
    with nd2.ND2File(file_path) as f:
        position_loops = [
            loop for loop in f.experiment
            if isinstance(loop, nd2.structures.XYPosLoop)
        ]
        if len(position_loops) != 1:
            raise NotImplementedError(
                f"Expected exactly one XY position loop, found {len(position_loops)}."
            )
        points = position_loops[0].parameters.points
    return np.array([[p.stagePositionUm.y, p.stagePositionUm.x] for p in points])


def scene_mosaic_positions_px(image: BioImage) -> np.ndarray:
    """Return the (Y, X) positions of the mosaic tiles stored as scenes, in pixels.

    Readers such as bioio-nd2 expose the tiles of a multipoint acquisition as scenes
    and do not implement `get_mosaic_tile_positions`, so the tile positions are
    reconstructed from the stage coordinates recorded in the file.

    Parameters
    ----------
    image : BioImage
        The BioImage object whose scenes are the mosaic tiles.

    Returns
    -------
    np.ndarray
        Tile positions in pixels, in the order of `image.scenes`.
    """
    file_path = str(image.reader._path)
    if not file_path.lower().endswith(".nd2"):
        raise NotImplementedError(
            "Mosaic positions of scene-based mosaics are only implemented for "
            f"ND2 files, got {file_path}."
        )
    positions_um = _nd2_stage_positions_um(file_path) * ND2_STAGE_TO_IMAGE_SIGNS
    if len(positions_um) != len(image.scenes):
        raise ValueError(
            f"The number of stage positions ({len(positions_um)}) does not match "
            f"the number of scenes ({len(image.scenes)})."
        )
    pixel_sizes_um = np.array(
        [image.physical_pixel_sizes.Y, image.physical_pixel_sizes.X]
    )
    return np.round(positions_um / pixel_sizes_um).astype(int)
