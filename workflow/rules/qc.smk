# rules/qc.smk

rule quality_control:
    input:
        csv = OUTPUT_DIR + "/postprocessed/{vid}.csv"
    output:
        traj = OUTPUT_DIR + "/qc/{vid}/{vid}_trajectory.png"
    params:
        summary_csv = OUTPUT_DIR + "/qc_summary.csv",
        outdir = OUTPUT_DIR + "/qc/{vid}/",
        vid_name = "{vid}"
    log:
        "logs/qc/{vid}.log"
    shell:
        """
        python scripts/qc_analytics.py \
            --input {input.csv} \
            --outdir {params.outdir} \
            --vid {params.vid_name} \
            --summary {params.summary_csv} > {log} 2>&1
        """
# THIS IS THE MISSING LINK:
rule aggregate_qc:
    input:
        expand(OUTPUT_DIR + "/qc/{vid}/{vid}_trajectory.png", vid=VIDEOS)
    output:
        OUTPUT_DIR + "/qc_summary.csv"
    run:
        # This ensures the file exists even if the expand finishes 
        # but the script somehow failed to append
        if not os.path.exists(output[0]):
            with open(output[0], 'w') as f:
                f.write("video,mean_conf,median_conf,frac_below_thresh\n")