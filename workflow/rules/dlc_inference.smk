rule dlc_inference:
    input:
        video=f"{RESIZED_DIR}/trimmed_{{vid}}.mp4",
        script="../src/dlc/run_dlc_inference.py"
    output:
        h5=f"{OUTPUT_DIR}/dlc_results/{{vid}}_superanimal.h5"
    log:
        f"{OUTPUT_DIR}/logs/{{vid}}_inference.log"
    params:
        out_dir=f"{OUTPUT_DIR}/dlc_results",
        model_arg=f"--superanimal {config.get('superanimal_model', 'superanimal_topviewmouse')}"
    shell:
        """

        python -u {input.script} \
            --videos {input.video} \
            --out_dir {params.out_dir} \
            --out_h5 {output.h5} \
            {params.model_arg} > {log} 2>&1
        """