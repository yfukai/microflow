params.output_path = null

process exportOriginalFilename {
    publishDir "${params.output_path}/${output_dir}", pattern: 'original_filename.txt', mode: "copy"

    input : 
        tuple val(output_dir), val(image_file_path)
    output :
        path("original_filename.txt")

    """
    echo '${image_file_path}' > original_filename.txt
    """

}