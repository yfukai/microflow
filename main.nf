nextflow.enable.dsl=2

params.input_path_csv = null
params.common_input_path = null
params.output_path = null
params.shading_correction = "none"
params.shading_correction_mode = "additive"
params.local_subtraction_channels = "all"

include { EXPORT_ORIGINAL_FILENAME } from "./modules/misc"
include { exportMetadata } from "./modules/export_metadata"
include { correctShading } from "./modules/correct_shading"

workflow {
    image_files = Channel.fromPath(params.input_path_csv) | splitCsv() \
        | filter { !(it[0] =~ /^#/) } | map({ 
            relpath=params.common_input_path.toURI()
                          .relativize(it[0].toURI())
                          .toString()
            [relpath+"_analyzed", it[0]] 
       })
    EXPORT_ORIGINAL_FILENAME(image_files)
    exportMetadata(image_files)
    metadata = exportMetadata.out[0]

    
    exportMetadata.out[0].collect(flat: false)
}

process stitching {
    errorStrategy 'retry'
    maxRetries 3
    maxForks 4 
    cpus 8 
    cache true

    publishDir "${params.output_path}/${output_dir}", \
        pattern: "{metadata.yaml,stitching_result.csv,d_stitching.ipynb}", \
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
    PYTHONPATH="${projectDir}/scripts" papermill ${projectDir}/scripts/d_stitching.ipynb \
        d_stitching.ipynb  \
        -p file_path shading_corrected.zarr \
        -p metadata_path "metadata.yaml" \
        -p output_image_path "stitched.zarr" \
        -p output_csv_path "stitching_result.csv" \
        -p every_t_stitch 0 \
        -p num_cpus 8 \
        -p target_channel '10x_Fukai_DIA_IS'
    """
}


//process report {
//    publishDir "${params.output_path}/${output_dir}", pattern: "report", mode: "copy"
//
//    input :
//    tuple file("stitched.zarr"), file("metadata.yaml"), val(output_dir) from stitchedMetadata
//
//    output : 
//    val(output_dir) into reported
//    file "report" 
//
//    """
//    ${moduleDir}/scripts/d_report.py \
//        stitched.zarr \
//        metadata.yaml \
//        report
//    """
//}
//
