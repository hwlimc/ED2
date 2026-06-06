#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ED2_ROOT="${ED2_ROOT:-${script_dir}}"
ED2_RUN_DIR="${ED2_RUN_DIR:-${ED2_ROOT}/ED/run}"
ED2_SIF="${ED2_SIF:-${ED2_ROOT}/ed2-mpi-intel.sif}"
ED2_INPUT="${ED2_INPUT:-ED2IN-fla.smoke}"
ED2_MPI_RANKS="${ED2_MPI_RANKS:-2}"
ED2_THREADS="${ED2_THREADS:-1}"

if [[ ! -d "${ED2_RUN_DIR}" ]]; then
   echo "Missing ED2 run directory: ${ED2_RUN_DIR}" >&2
   exit 2
fi

if [[ ! -s "${ED2_RUN_DIR}/${ED2_INPUT}" ]]; then
   echo "Missing ED2 namelist: ${ED2_RUN_DIR}/${ED2_INPUT}" >&2
   exit 2
fi

if [[ ! -s "${ED2_SIF}" ]]; then
   echo "Missing MPI Apptainer image: ${ED2_SIF}" >&2
   echo "Build it first with: ./build_mpi_sif.sh" >&2
   exit 2
fi

if command -v apptainer >/dev/null 2>&1; then
   container_cmd=apptainer
elif command -v singularity >/dev/null 2>&1; then
   container_cmd=singularity
else
   echo "Neither apptainer nor singularity is available in PATH." >&2
   exit 127
fi

export OMP_NUM_THREADS="${ED2_THREADS}"
export APPTAINERENV_OMP_NUM_THREADS="${OMP_NUM_THREADS}"
export SINGULARITYENV_OMP_NUM_THREADS="${OMP_NUM_THREADS}"

echo "ED2 root:       ${ED2_ROOT}"
echo "Run directory:  ${ED2_RUN_DIR}"
echo "MPI SIF image:  ${ED2_SIF}"
echo "Namelist:       ${ED2_INPUT}"
echo "Container:      ${container_cmd}"
echo "MPI ranks:      ${ED2_MPI_RANKS}"
echo "OMP threads:    ${OMP_NUM_THREADS}"
echo "Stack before:   $(ulimit -s)"

cd "${ED2_RUN_DIR}"
ulimit -s unlimited
echo "Stack after:    $(ulimit -s)"

exec "${container_cmd}" exec \
   --bind "${ED2_ROOT}:${ED2_ROOT}" \
   "${ED2_SIF}" \
   bash -lc "cd '${ED2_RUN_DIR}' && ulimit -s unlimited && export OMP_NUM_THREADS='${OMP_NUM_THREADS}' && exec mpirun --oversubscribe --bind-to none -np '${ED2_MPI_RANKS}' ed2 -f '${ED2_INPUT}'"
