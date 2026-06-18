# Ingest Files

## 1. Download the script to your computer
You will have to download this script on your local machine. The script is located at icmh-dlc-final-scripts/sharepoint_of_downloader.py

## 2. Run the script to grab your cookies
Run the script with `python sharepoint_of_downloader.py login` Make sure you have selenium and chromedriver installed before you run the script. You will have to login to your IU account on the popup browser. Wait about 30 seconds and a file named `sp_auth.json` will be downloaded to the same directory that the script was run in.

## 3. Upload sp_auth.json to HPC directory
Upload the generated authentication file to the same directory as the sharepoint_of_downloader.py on the HPC

## 4. Replace the username in the sharepoint_downloader.py file with your username

## 5. Replace the URL in the sharepoint_downloader.py file with the new URL

## 6. Run sbatch downloader_job.sh from the icmh-dlc-final-scripts directory

## 7. IMPORTANT: Delete token (sp_auth.json) from HPC after all videos downloaded (slurm script finishes)