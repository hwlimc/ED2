#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ED2_ROOT="${ED2_ROOT:-${script_dir}}"
ED2_RUN_DIR="${ED2_RUN_DIR:-${ED2_ROOT}/ED/run}"
ED2_SIF="${ED2_SIF:-${ED2_ROOT}/ed2-intel.sif}"
ED2_INPUT="${ED2_INPUT:-ED2IN-fla.smoke}"

default_threads="$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 1)"
ED2_THREADS="${ED2_THREADS:-${OMP_NUM_THREADS:-${default_threads}}}"

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
