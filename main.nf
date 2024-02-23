nextflow.enable.dsl=2

params.input_path_csv = null
params.common_input_path = null
params.output_path = null
params.shading_correction = "none"
params.shading_correction_mode = "additive"
params.local_subtraction_channels = "all"

include { EXPORT_ORIGINAL_FILENAME } from "./modules/misc"
include { EXPORT_METADATA } from "./modules/export_metadata"
include { ESTIMATE_SHADING_EACH; CORRECT_SHADING_EACH } from "./modules/correct_shading"
include { STITCHING } from "./modules/stitching"

workflow {
    image_files = Channel.fromPath(params.input_path_csv) | splitCsv() \
        | filter { !(it[0] =~ /^#/) } | map({ 
            relpath=params.common_input_path.toURI()
                          .relativize(it[0].toURI())
                          .toString()
            [relpath+"_analyzed", it[0]] 
       })
    EXPORT_ORIGINAL_FILENAME(image_files)
    EXPORT_METADATA(image_files)

    metadata = EXPORT_METADATA.out[0]
    image_files.join(metadata).set { image_files_metadata }
    ESTIMATE_SHADING_EACH(image_files_metadata)

    shading_profiles = ESTIMATE_SHADING_EACH.out[0]
    image_files_metadata.join(shading_profiles).set { image_files_metadata_shading_profiles }
    CORRECT_SHADING_EACH(image_files_metadata_shading_profiles)

    shading_corrected = CORRECT_SHADING_EACH.out[0]
    metadata.join(shading_corrected).set { image_files_metadata_shading_corrected }
    //image_files_metadata_shading_corrected.view()
    STITCHING(image_files_metadata_shading_corrected)

}

