params.output_path = null

process EXPORT_ORIGINAL_FILENAME {
    publishDir "${params.output_path}/${meta.output_dir}", pattern: 'original_filename.txt', mode: "copy"

    input : 
        tuple val(meta), val(image_file_path)
    output :
        path("original_filename.txt")

    """
    echo '${image_file_path}' > original_filename.txt
    """

}