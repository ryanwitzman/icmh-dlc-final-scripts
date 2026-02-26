srun --partition=gpu --gpus-per-node=1 --account=r01704 --time=00:10:00 --pty bash

module load cudatoolkit/11.8
conda activate icmh-dlc-310

# Check 1: can TF see the GPU?
python -c "import tensorflow as tf; print(tf.config.list_physical_devices('GPU'))"

# Check 2: is cuDNN bundled in the env?
find $CONDA_PREFIX -name "libcudnn*" 2>/dev/null | head -5