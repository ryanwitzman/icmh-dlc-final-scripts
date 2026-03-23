rule postprocess:
    input:
        h5=lambda wildcards: find_existing_output(wildcards.vid, "dlc_results", "{vid}_superanimal.h5"),
        script = "../src/postprocess/h5_to_csv.py"
    output:
        csv=f"{OUTPUT_DIR}/postprocessed/{BATCH_ID}/{{vid}}.csv"
    params:
        pcutoff=config.get("pcutoff", 0.6)
    log:
        f"{LOG_DIR}/{{vid}}_postprocess.log"
    shell:
        """
        python3 ../src/postprocess/h5_to_csv.py \
            --h5 {input.h5} \
            --out_csv {output.csv} \
            --log_file {log} \
            --pcutoff {params.pcutoff}
        """