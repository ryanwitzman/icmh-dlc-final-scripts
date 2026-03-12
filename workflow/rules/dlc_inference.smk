rule dlc_inference:
    input:
        video=lambda wildcards: find_existing_output(wildcards.vid, "trimmed_resized", "trimmed_{vid}.mp4"),
        script="../src/dlc/run_dlc_inference.py"
    output:
        h5=f"{OUTPUT_DIR}/dlc_results/{BATCH_ID}/{{vid}}_superanimal.h5"
    log:
        f"{LOG_DIR}/{{vid}}_inference.log"
    params:
        out_dir=f"{OUTPUT_DIR}/dlc_results/{BATCH_ID}",
        model_arg=f"--superanimal {config.get('superanimal_model', 'superanimal_topviewmouse')}"
    shell:
        """
        python -u {input.script} \
            --videos {input.video} \
            --out_dir {params.out_dir} \
            --out_h5 {output.h5} \
            {params.model_arg} > {log} 2>&1
        """