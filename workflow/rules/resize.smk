# ---------------------------------------------------------------------------
# resize.smk
# Downsample trimmed videos before DLC inference to reduce GPU load.
#
# Why: DLC SuperAnimal runs multi-scale inference (e.g. [1030,1080,1130]).
# At 1920x1080 this is 3x full-HD compute per frame. Downsampling to 960x540
# keeps all three scales well under 600px, cutting GPU work by ~75% with no
# meaningful loss in top-view mouse keypoint accuracy.
#
# Target resolution: 960x540 (half of 1920x1080, keeps aspect ratio exact).
# Change RESIZE_SCALE below to adjust:
#   "iw/2:ih/2"  → 960x540  (recommended, ~4x speedup)
#   "iw/3:ih/3"  → 640x360  (aggressive, fine for mice under good lighting)
# ---------------------------------------------------------------------------

RESIZE_SCALE = config.get("resize_scale", "iw/2:ih/2")

# Resized videos go into their own subdirectory so originals are preserved.
RESIZED_DIR = f"{OUTPUT_DIR}/trimmed_resized"

rule resize_for_dlc:
    input:
        video=f"{OUTPUT_DIR}/trimmed_{{vid}}.mp4"
    output:
        video=f"{RESIZED_DIR}/trimmed_{{vid}}.mp4"
    params:
        scale=RESIZE_SCALE
    log:
        f"{OUTPUT_DIR}/logs/{{vid}}_resize.log"
    shell:
        """
        ffmpeg -y \
            -i {input.video} \
            -vf "scale={params.scale}" \
            -c:v libx264 -crf 18 -preset fast \
            -an \
            {output.video} \
            > {log} 2>&1
        """