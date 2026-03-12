rule postprocess:
    input:
        h5=f"{BATCH_DIR}/dlc_results/{{vid}}_superanimal.h5",
        script = "../src/postprocess/h5_to_csv.py"
    output:
        csv=f"{BATCH_DIR}/postprocessed/{{vid}}.csv"
    params:
        pcutoff=config.get("pcutoff", 0.6)
    log:
        f"{BATCH_DIR}/logs/{{vid}}_postprocess.log"
    shell:
        """
        python ../src/postprocess/h5_to_csv.py \
            --h5 {input.h5} \
            --out_csv {output.csv} \
            --log_file {log} \
            --pcutoff {params.pcutoff}
        """