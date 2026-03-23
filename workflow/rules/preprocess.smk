rule trim_video:
    input:
        video  = lambda wildcards: PATH_MAP[wildcards.vid],
        script = "../src/preprocess/trim_video.py"
    output:
        video  = f"{OUTPUT_DIR}/trimmed/{BATCH_ID}/trimmed_{{vid}}.mp4"
    log:
        f"{LOG_DIR}/{{vid}}_preprocess.log"
    shell:
        # FIX: Changed 'script:' to 'shell:' so it runs as a standard CLI command
        """
        python3 {input.script} \
            --video {input.video} \
            --out {output.video} > {log} 2>&1
        """