process EXPORT_METADATA {
    conda "${moduleDir}/env/conda.yaml"
    cache true
    errorStrategy "finish"

    publishDir "${params.output_path}/${meta.output_dir}", pattern: '{metadata.yaml}', mode: "copy"
    publishDir "${params.output_path}/${meta.output_dir}/qc/export_metadata/", pattern: 'stitched_*.png', mode: "copy"

    input : 
    tuple val(meta), path(image_file_path)

    output :
    tuple val(meta), path("metadata.yaml"), path("scenes_channels.yaml")
    path("stitched_*.png")

    """
    export_metadata.py \
        --file_path ${image_file_path} \
        --output_path ./ \
        --output_metadata_filename metadata.yaml \
        --output_test_image_filename_prefix stitched 
    # Extract "channel_names" from metadata.yaml for further processing
    yaml_extract_channels.py > scenes_channels.yaml
    """
}
