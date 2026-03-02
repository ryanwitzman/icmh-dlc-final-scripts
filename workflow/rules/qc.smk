rule quality_control:
    input:
        csv = OUTPUT_DIR + "/postprocessed/{vid}.csv"
    output:
        plots = report(directory(OUTPUT_DIR + "/qc/{vid}/"), category="QC Plots"),
        traj  = OUTPUT_DIR + "/qc/{vid}/{vid}_trajectory.png"
    log:
        f"{OUTPUT_DIR}/logs/{{vid}}_qc.log"
    params:
        summary_csv = OUTPUT_DIR + "/qc_summary.csv",
        vid_name = "{vid}"
    shell:
        """
        python ../src/qc/qc_analytics.py \
            --input {input.csv} \
            --outdir {output.plots} \
            --vid {params.vid_name} \
            --summary {params.summary_csv}
        """