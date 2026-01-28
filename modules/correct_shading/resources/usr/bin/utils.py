from dask import array as da

def read_mosaic_image(image,mosaic_dim,dimension,**kwargs):
    if mosaic_dim == "M":
        da_image = image.get_image_dask_data("M"+dimension,**kwargs)
    elif mosaic_dim == "I":
        image_data = []
        for scene in image.scenes:
            image.set_scene(scene)
            image_data.append(image.get_image_dask_data(dimension,**kwargs))
        da_image = da.array(image_data)
    else:
        raise ValueError(f"Unsupported mosaic dimension: {mosaic_dim}")
    new_chunks = [1,] + [-1 if d in ["Z", "Y", "X"] else 1 
                         for i, d in enumerate(dimension)]
    print(f"Rechunking image from {da_image.chunks} to {new_chunks}")
    return da_image.rechunk(tuple(new_chunks))