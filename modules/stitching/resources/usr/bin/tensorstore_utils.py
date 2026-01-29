import tensorstore as ts
def init_store(path, dtype=None, shape=None, chunks=None, mode="r", codecs=None):
    if chunks is None:
        chunks = shape
    if mode not in ["r", "w", "a"]:
        raise ValueError("mode must be 'r', 'w', or 'a'")
    spec = {
        "driver": "zarr3",
        "kvstore": {"driver": "file", "path": path},
        "context": {"cache_pool": {"total_bytes_limit": 100_000_000}},
    }
    if codecs is not None:
        spec["metadata"] = {
            "codecs": codecs,
        }
    if mode == "r":
        spec["open"] = True
        spec["create"] = False
    elif mode == "w":
        spec["create"] = True
        spec["open"] = False
        spec["delete_existing"] = True
    elif mode == "a":
        spec["create"] = True
        spec["open"] = True
        spec["delete_existing"] = False
    chunk_layout = ts.ChunkLayout(chunk_shape=list(chunks)) if chunks is not None else None
    return ts.open(spec, 
                   shape=list(shape) if shape is not None else None,
                   dtype=dtype,
                   chunk_layout=chunk_layout).result()
codecs_image = [{
    "name": "blosc",
    "configuration": {"cname": "zstd", "clevel": 5,
                      "shuffle": "bitshuffle"}
}]
codecs_label = [{
    "name": "zstd",
    "configuration": {"level": 15}
}]