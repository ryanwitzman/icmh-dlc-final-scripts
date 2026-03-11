
    output:
        flag     = touch(INGEST_FLAG),
        manifest = MANIFEST
    params:
        sharepoint_url = config["sharepoint_url"],
        remote_path    = config["remote_path"],
        staging_dir    = STAGING_DIR,
        tenant_id      = config["tenant_id"],
        client_id      = config["client_id"],
        batch_id       = BATCH_ID,
    log:
        f"{LOG_DIR}/{BATCH_ID}_ingest_snakemake.log"
    shell:
        """
        python ../src/ingest/hpc_ingest.py \
            --sharepoint-url  "{params.sharepoint_url}" \
            --remote-path     "{params.remote_path}" \
            --staging-dir     "{params.staging_dir}" \
            --tenant-id       "{params.tenant_id}" \
            --client-id       "{params.client_id}" \
            --batch-id        "{params.batch_id}" \
            --skip-existing \
        > {log} 2>&1
        """

rule validate_transfer:
    input:
        flag     = INGEST_FLAG,
        manifest = MANIFEST,
    output:
        touch(f"{LOG_DIR}/{BATCH_ID}.validated.done")
    run:
        import csv, sys
        failed = []
        with open(input.manifest, newline="") as f:
            for row in csv.DictReader(f):
                if row["status"] not in ("OK", "SKIPPED"):
                    failed.append(f"{row['remote_path']}  [{row['status']}]  {row['notes']}")
        if failed:
            print("VALIDATION FAILED — the following files did not transfer cleanly:")
            for line in failed:
                print("  ✗", line)
            sys.exit(1)
        print(f"Validation passed: all files in {input.manifest} are OK.")