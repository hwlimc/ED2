#!/bin/bash
#SBATCH --job-name=ed2-fla-smoke
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --output=ed2-fla-smoke-%j.out
#SBATCH --error=ed2-fla-smoke-%j.err
#
# Uncomment and edit these if your HPC requires them:
##SBATCH --partition=your_partition
##SBATCH --account=your_account

set -euo pipefail

# This script is meant to be submitted from this repository, or run in place from
# ED/Template/scripts/SLURM. Override these variables at submit time if needed:
#   sbatch --export=ALL,ED2_ROOT=/path/to/ED2,ED2_SIF=/path/to/ed2-intel.sif run_ed2_sif_smoke.sbatch
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
default_root="$(cd "${script_dir}/../../../.." && pwd)"

ED2_ROOT="${ED2_ROOT:-${default_root}}"
ED2_RUN_DIR="${ED2_RUN_DIR:-${ED2_ROOT}/ED/run}"
ED2_SIF="${ED2_SIF:-${ED2_ROOT}/ed2-intel.sif}"
ED2_INPUT="${ED2_INPUT:-ED2IN-fla.smoke}"

if [[ ! -d "${ED2_RUN_DIR}" ]]; then
   echo "Missing ED2 run directory: ${ED2_RUN_DIR}" >&2
   exit 2
fi

if [[ ! -s "${ED2_RUN_DIR}/${ED2_INPUT}" ]]; then
   echo "Missing ED2 namelist: ${ED2_RUN_DIR}/${ED2_INPUT}" >&2
   exit 2
fi

if [[ ! -s "${ED2_SIF}" ]]; then
   echo "Missing Apptainer image: ${ED2_SIF}" >&2
   exit 2
fi

if ! command -v apptainer >/dev/null 2>&1; then
   module load apptainer 2>/dev/null || module load singularity 2>/dev/null || true
fi

if command -v apptainer >/dev/null 2>&1; then
   container_cmd=apptainer
elif command -v singularity >/dev/null 2>&1; then
   container_cmd=singularity
else
   echo "Neither apptainer nor singularity is available. Load the container module first." >&2
   exit 127
fi

export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-16}"
export APPTAINERENV_OMP_NUM_THREADS="${OMP_NUM_THREADS}"
export SINGULARITYENV_OMP_NUM_THREADS="${OMP_NUM_THREADS}"

echo "ED2 root:       ${ED2_ROOT}"
echo "Run directory:  ${ED2_RUN_DIR}"
echo "SIF image:      ${ED2_SIF}"
echo "Namelist:       ${ED2_INPUT}"
echo "Container:      ${container_cmd}"
echo "OMP threads:    ${OMP_NUM_THREADS}"
echo "Stack before:   $(ulimit -s)"

cd "${ED2_RUN_DIR}"
ulimit -s unlimited
echo "Stack after:    $(ulimit -s)"

exec "${container_cmd}" exec \
   --bind "${ED2_ROOT}:${ED2_ROOT}" \
   "${ED2_SIF}" \
   bash -lc "cd '${ED2_RUN_DIR}' && ulimit -s unlimited && exec ed2 -f '${ED2_INPUT}'"
