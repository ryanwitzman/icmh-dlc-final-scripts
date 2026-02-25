rule dlc_inference:
    input:
        video=f"{OUTPUT_DIR}/trimmed_{{vid}}.mp4"
    output:
        # We track the log file as the output to handle DLC's dynamic h5 naming
        log_file=f"{OUTPUT_DIR}/logs/{{vid}}_inference.log"
    params:
        out_dir=f"{OUTPUT_DIR}/dlc_results"
    resources:
        # Requesting GPU and memory via Snakemake resources (for Slurm parsing)
        gpus=1,
        mem_mb=16000,
        time="04:00:00"
    shell:
        """
        python ../src/dlc/run_dlc_inference.py \
            --videos {input.video} \
            --out_dir {params.out_dir} \
            --log_file {output.log_file}
        """