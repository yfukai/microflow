process EXPORT_METADATA {
    conda "${moduleDir}/env/conda.yaml"

    cache true

    publishDir "${params.output_path}/${output_dir}", pattern: '{metadata.yaml}', mode: "copy"
    publishDir "${params.output_path}/${output_dir}/qc/export_metadata/", pattern: '{stitched.png}', mode: "copy"

    input : 
    tuple val(output_dir), path(image_file_path)

    output :
    tuple val(output_dir), path("metadata.yaml")
    path("stitched.png")

    """
    export_metadata.py \
        --file_path ${image_file_path} \
        --output_metadata_path metadata.yaml
        --output_test_image_path stitched.png
    """
}
