process EXPORT_METADATA {
    conda "${moduleDir}/env/conda.yaml"
    cache true
    errorStrategy "finish"

    publishDir "${params.output_path}/${output_dir}", pattern: '{metadata.yaml}', mode: "copy"
    publishDir "${params.output_path}/${output_dir}/qc/export_metadata/", pattern: 'stitched_*.png', mode: "copy"

    input : 
    tuple val(output_dir), path(image_file_path)

    output :
    tuple val(output_dir), path("metadata.yaml")
    path("stitched_*.png")

    """
    export_metadata.py \
        --file_path ${image_file_path} \
        --output_path ./ \
        --output_metadata_filename metadata.yaml \
        --output_test_image_filename_prefix stitched 
    """
}
