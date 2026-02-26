rule postprocess:
    input:
        h5=f"{OUTPUT_DIR}/dlc_results/{{vid}}_superanimal.h5"
    output:
        csv=f"{OUTPUT_DIR}/postprocessed/{{vid}}.csv"
    params:
        pcutoff=config.get("pcutoff", 0.6)
    log:
        f"{OUTPUT_DIR}/logs/{{vid}}_postprocess.log"
    shell:
        """
        python ../src/postprocess/h5_to_csv.py \
            --h5 {input.h5} \
            --out_csv {output.csv} \
            --log_file {log} \
            --pcutoff {params.pcutoff}
        """