from dask import array as da

def read_mosaic_image(image,mosaic_dim,dimension,**kwargs):
    if mosaic_dim == "M":
        return image.get_image_dask_data("M"+dimension,**kwargs)
    elif mosaic_dim == "I":
        image_data = []
        for scene in image.scenes:
            image.set_scene(scene)
            image_data.append(image.get_image_dask_data(dimension,**kwargs))
        return da.array(image_data)
    else:
        raise ValueError(f"Unsupported mosaic dimension: {mosaic_dim}")