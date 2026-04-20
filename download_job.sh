#!/bin/bash
#SBATCH --job-name=sp_download
#SBATCH --partition=general
#SBATCH --account=r01704        # Using your project folder name as the assumed account
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --time=12:00:00         # Gives the script 12 hours to finish
#SBATCH --mem=4G                # Allocates 4 GB of RAM
#SBATCH --output=download.log   # Saves the live terminal output to this file

module load conda/25.3.0
conda activate icmh-dlc-310
cd /N/project/msk_dl/icmh-dlc-final-scripts
python sharepoint_of_downloader.py download --auth sp_auth.json