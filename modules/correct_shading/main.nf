process estimateShadingEach {
//    errorStrategy 'retry'
//    maxForks 2 
//    maxRetries 3
//    cache true
//    cpus 10

//    publishDir "${params.output_path}/${output_dir}", pattern: 'b*_shading_correction*.ipynb', mode: "copy"
//    publishDir "${params.output_path}/${output_dir}", pattern: 'shading_corrected.zarr', mode: "symlink"
    
//    input:
//    val collectedInputs

 //   output:
 //   tuple path("shading_corrected.zarr"), path("metadata.yaml"), val(output_dir)
 //   path("b1_shading_correction_median.ipynb")

   """
   PYTHONPATH="${projectDir}/scripts" papermill ${projectDir}/scripts/b1_shading_correction_median.ipynb \
       c_shading_correction.ipynb  \
       -p file_paths "[../testdata/test1.nd2,../testdata/test2.nd2,../testdata/test3.nd2]"
       -p output_dirs "[../testdata/test1_output,../testdata/test2_output,../testdata/test3_output]"
       -p metadata_paths "[../testdata/test1_output/test1_metadata.yaml,../testdata/test2_output/test2_metadata.yaml,../testdata/test3_output/test3_metadata.yaml]"
       -p common_output_dir ./
       -p corrected_filename "shading_corrected.zarr"
       -p profile_filename "shading_profile.zarr"
       -p mode "additive"
       -p strategy "timewise"
       -p robust False
       -p local_subtraction_channels ${params.local_subtraction_channels} 
       -p local_subtraction_channels "*DIA*"
       -p local_subtraction_scaling 0.1
       -p local_subtraction_median_disk_size 4
       -p num_cpus 10 \
       -p mode ${params.shading_correction_mode} \
   """
}