process exportMetadata {
    errorStrategy 'retry'
    maxForks 20
    maxRetries 3
    cache true

    publishDir "${params.output_path}/${output_dir}", pattern: '{a_export_metadata.ipynb,metadata.yaml}', mode: "copy"

    input : 
    tuple path(image_file_path), val(output_dir)

    output :
    tuple path(image_file_path), path("metadata.yaml"), val(output_dir)
    file("a_export_metadata.ipynb")

    """
    PYTHONPATH="${projectDir}/scripts" papermill ${projectDir}/scripts/a_export_metadata.ipynb \
        a_export_metadata.ipynb \
        -p file_path ${image_file_path} \
        -p output_metadata_path metadata.yaml
    """
}
