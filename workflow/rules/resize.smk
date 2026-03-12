RESIZE_SCALE = config.get("resize_scale", "iw/2:ih/2")

rule resize_for_dlc:
    input:
        video=f"{BATCH_DIR}/trimmed_{{vid}}.mp4"
    output:
        video=f"{RESIZED_DIR}/trimmed_{{vid}}.mp4"
    params:
        scale=RESIZE_SCALE
    log:
        f"{BATCH_DIR}/logs/{{vid}}_resize.log"
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