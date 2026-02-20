"""
rules/preprocess.smk
Preprocessing rules (trim, etc.) that operate on files already in staging.
PATH_MAP, STAGING_DIR, and OUTPUT_DIR are inherited from the master Snakefile.
"""

rule trim_video:
    input:
        video    = lambda wildcards: PATH_MAP[wildcards.vid],
        validated = f"{LOG_DIR}/{BATCH_ID}.validated.done"   # blocks until ingest + validation pass
    output:
        f"{OUTPUT_DIR}/trimmed_{{vid}}"
    log:
        f"{OUTPUT_DIR}/logs/trim_{{vid}}.log"
    script:
        "../src/trim/trim_video.py"