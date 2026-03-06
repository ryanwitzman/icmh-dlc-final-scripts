# Troubleshooting

## Locked Directory
If a Slurm job dies or you kill Snakemake manually, the working directory gets locked.
**Fix:** 
```bash
snakemake --unlock
```

## Incomplete Files
If a job was killed while writing a file, Snakemake will flag it as incomplete on the next run.
**Fix:** 
```bash
snakemake --cleanup-metadata <file>
```
Or just delete the file and let Snakemake regenerate it.

## Slurm OOM (Out of Memory)
If inference or resizing fails without a clear python error, Slurm probably killed it for using too much memory.
**Fix:** Increase the `mem` requested in `workflow/cluster.yaml`. `dlc_inference` is at `16G`, `preprocess` is at `8G`. 

## GPU Not Assigned
If inference is taking hours, it might be running on a CPU node. 
**Fix:** 
- Check `workflow/cluster.yaml` to ensure it's pointing to the `gpu` partition.
- Check `use_gpu: true` in `configs/config.yaml`.
- Run `squeue -u <username>` to see if it actually got a GPU node.

## FFmpeg Errors
The resize rule needs FFmpeg 6.1. Older versions might break the command.
**Fix:** Check your version with `ffmpeg -version`. If it's wrong, reinstall FFmpeg or recreate the conda environment.

## Output is all NaN
If the post-processed CSVs are full of `NaN`s, the network confidence was too low.
**Fix:** The `pcutoff` in `configs/config.yaml` is 0.6. If the lighting is bad or the video is weird, DLC might be giving low likelihoods. You can lower the cutoff, or check if the `superanimal_topviewmouse` model actually makes sense for the video angle.
