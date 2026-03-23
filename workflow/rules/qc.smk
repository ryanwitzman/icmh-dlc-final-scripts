import pandas as pd
import os

rule quality_control:
    input:
        csv=lambda wildcards: find_existing_output(wildcards.vid, "postprocessed", "{vid}.csv"),
        script = "../src/qc/qc_analytics.py"
    output:
        traj    = f"{OUTPUT_DIR}/qc/{BATCH_ID}/{{vid}}/{{vid}}_trajectory.png",
        heatmap = f"{OUTPUT_DIR}/qc/{BATCH_ID}/{{vid}}/{{vid}}_heatmap.png",
        speed   = f"{OUTPUT_DIR}/qc/{BATCH_ID}/{{vid}}/{{vid}}_speed.png",
        stats   = f"{OUTPUT_DIR}/qc/{BATCH_ID}/{{vid}}/{{vid}}_stats.csv"
    params:
        outdir   = f"{OUTPUT_DIR}/qc/{BATCH_ID}/{{vid}}/",
        vid_name = "{vid}"
    log:
        f"{LOG_DIR}/{{vid}}_qc.log"
    shell:
        """
        python3 {input.script} \
            --input {input.csv} \
            --outdir {params.outdir} \
            --vid {params.vid_name} \
            --stats_out {output.stats} > {log} 2>&1
        """

rule aggregate_qc:
    input:
        stats = STATS_PATHS
    output:
        summary = f"{OUTPUT_DIR}/qc/{BATCH_ID}/qc_summary.csv"
    run:
        df_list = [pd.read_csv(f) for f in input.stats]
        if df_list:
            final_df = pd.concat(df_list, ignore_index=True)
            final_df.to_csv(output.summary, index=False)
        else:
            with open(output.summary, 'w') as f:
                f.write("video,mean_conf,median_conf,frac_below_thresh\n")