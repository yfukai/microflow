import numpy as np
from dask import array as da
import pandas as pd
from itertools import combinations
import networkx as nx

def merge_mosaic_images(images, mosaic_positions, add_mosaics = False):
    """Merge images into a mosaic image.
    
    Parameters
    ----------
    images : list of np.ndarray
        List of images to merge.
    
    mosaic_positions : list of tuple of int
        List of positions of images in the mosaic.
    
    Returns
    -------
    np.ndarray
        Mosaic image.
    """

    mosaic_positions = (mosaic_positions - np.min(mosaic_positions, axis=0)[np.newaxis]).round().astype(int)
    
    # Get the size of the mosaic image
    mosaic_size = np.max(mosaic_positions, axis=0) + np.array(images[0].shape[-2:])
    
    # Create the mosaic image
    mosaic = np.zeros(mosaic_size, dtype=images.dtype)
    
    # Merge images into the mosaic image
    for image, position in zip(images, mosaic_positions):
        mosaic[position[0]:position[0] + image.shape[0],
               position[1]:position[1] + image.shape[1]] = image
    return mosaic


def _calc_overlap_area_ratio(image_shape,relative_pos):
    """Calculate the image overlap area ratio with respect to the image area.
    
    """
    percentage = 1.
    for s, p in zip(image_shape,relative_pos):
        percentage *= np.clip(1-np.abs(p/s),0,None)
    return percentage


def parse_positions_to_pairs(
    image_shape,
    tile_indices = None, 
    estimated_positions = None,
    overlap_threshold_percentage : float = 5,
    ):
    """Parse image positions to image pairs.

    Parameters
    ----------
    image_shape : List[Int]
        The shape of a single input image.
    tile_indices : Optional[IntArray], optional
        The integer index of the tiles. If None, `estimated_positions` must be supplied.
    estimated_positions : Optional[NumArray], optional
        The estimated position of the tiles in pixel. If None, `tile_indices` must be supplied.
    overlap_threshold_percentage : float, optional
        The area percentage threshold to calculate pair displacement between tiles. Effective only when tile_indices is None.
    """

    image_pairs = []
    if tile_indices is not None:
        for (j1,ind1), (j2,ind2) in combinations(enumerate(tile_indices),2):
            # if the images are the next to each other or at the same position
            diff = np.abs(ind1 - ind2)
            if ((np.max(diff) == 1 and np.sum(diff == 1) == 1)) or np.all(ind1 == ind2): 
                if estimated_positions is not None:
                    dpos = estimated_positions[j2]-estimated_positions[j1]
                else:
                    dpos = None
                image_pairs.append({
                    "image_index1":j1,
                    "image_index2":j2,
                    "index_displacement":ind2-ind1,
                    "estimated_displacement":dpos,
                }) # image 2 position with respect to image 1
    else:
        for (j1,pos1), (j2,pos2) in combinations(enumerate(estimated_positions),2):
            if _calc_overlap_area_ratio(image_shape,np.array(pos2)-np.array(pos1)) > overlap_threshold_percentage/100:
                image_pairs.append({
                    "image_index1":j1,
                    "image_index2":j2,
                    "index_displacement":None,
                    "estimated_displacement":pos2-pos1
                })
    
    if len(image_pairs) == 0:
        raise RuntimeError("There is no valid image pairs. Please check tile_indices and estimated_positions.")

    pairs_df = pd.DataFrame.from_records(image_pairs)
    pairs_graph = nx.Graph()
    nodes_count = len(estimated_positions if estimated_positions is not None else tile_indices) 
    pairs_graph.add_nodes_from(range(nodes_count))
    pairs_graph.add_edges_from(pairs_df[["image_index1","image_index2"]].values)

    if len(list(nx.connected_components(pairs_graph))) > 1:
        raise ValueError("Parsing positions resulted more than one connected graphs.")

    return pairs_df
