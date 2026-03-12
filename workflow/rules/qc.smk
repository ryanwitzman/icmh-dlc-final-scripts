import pandas as pd
import os

rule quality_control:
    input:
        csv = BATCH_DIR + "/postprocessed/{vid}.csv",
        script = "../src/qc/qc_analytics.py"
    output:
        traj    = BATCH_DIR + "/qc/{vid}/{vid}_trajectory.png",
        heatmap = BATCH_DIR + "/qc/{vid}/{vid}_heatmap.png",
        speed   = BATCH_DIR + "/qc/{vid}/{vid}_speed.png",
        stats   = BATCH_DIR + "/qc/{vid}/{vid}_stats.csv"
    params:
        outdir   = BATCH_DIR + "/qc/{vid}/",
        vid_name = "{vid}"
    log:
        BATCH_DIR + "/logs/{vid}_qc.log"
    shell:
        """
        python {input.script} \
            --input {input.csv} \
            --outdir {params.outdir} \
            --vid {params.vid_name} \
            --stats_out {output.stats} > {log} 2>&1
        """

rule aggregate_qc:
    input:
        stats = STATS_PATHS
    output:
        summary = BATCH_DIR + "/qc/qc_summary.csv"
    run:
        df_list = [pd.read_csv(f) for f in input.stats]
        if df_list:
            final_df = pd.concat(df_list, ignore_index=True)
            final_df.to_csv(output.summary, index=False)
        else:
            with open(output.summary, 'w') as f:
                f.write("video,mean_conf,median_conf,frac_below_thresh\n")