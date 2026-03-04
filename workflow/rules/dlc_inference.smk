rule dlc_inference:
    input:
        video=f"{OUTPUT_DIR}/trimmed_{{vid}}.mp4"
    output:
        h5=f"{OUTPUT_DIR}/dlc_results/{{vid}}_superanimal.h5",
        log_file=f"{OUTPUT_DIR}/logs/{{vid}}_inference.log"
    params:
        out_dir=f"{OUTPUT_DIR}/dlc_results",
        model_arg=f"--superanimal {config.get('superanimal_model', 'superanimal_topviewmouse')}",
    shell:
        """
        python ../src/dlc/run_dlc_inference.py \
            --videos {input.video} \
            --out_dir {params.out_dir} \
            --out_h5 {output.h5} \
            --log_file {output.log_file} \
            {params.model_arg}
        """