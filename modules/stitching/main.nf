process STITCHING {
    errorStrategy 'retry'
    maxRetries 3
    maxForks 4 
    cpus 8 
    cache true

    publishDir "${params.output_path}/${output_dir}", \
        pattern: "{metadata.yaml,stitching_result.csv}", \
        mode: "copy"
    publishDir "${params.output_path}/${output_dir}/notebooks", \
        pattern: "{*.ipynb}", \
        mode: "copy"
    publishDir "${params.output_path}/${output_dir}", \
        pattern: "stitched.zarr", \
        mode: "symlink"

    input :
    tuple path("shading_corrected.zarr"), path("metadata.yaml"), val(output_dir)

    output :
    tuple path("stitched.zarr"), path("metadata.yaml"), val(output_dir)
    path "stitching_result.csv" 
    path "d_stitching.ipynb"

    """
    PYTHONPATH="${projectDir}/scripts" papermill ${projectDir}/scripts/c_stitching.ipynb \
        c_stitching.ipynb  \
        -p file_path shading_corrected.zarr \
        -p metadata_path "metadata.yaml" \
        -p output_image_path "stitched.zarr" \
        -p output_csv_path "stitching_result.csv" \
        -p every_t_stitch 0 \
        -p num_cpus 8 \
        -p target_channel '10x_Fukai_DIA_IS'
    """
}