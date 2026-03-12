rule trim_video:
    input:
        video    = lambda wildcards: PATH_MAP[wildcards.vid],
        script = "../src/preprocess/trim_video.py"
    output:
        f"{BATCH_DIR}/trimmed_{{vid}}.mp4"
    log:
        f"{BATCH_DIR}/logs/{{vid}}_preprocess.log"
    script:
        "../../src/preprocess/trim_video.py"