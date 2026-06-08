#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd "${script_dir}/.." && pwd)"
repo_root="$(cd "${project_root}/../.." && pwd)"
config_dir="${ED2_RUN_DIR:-${project_root}/config}"

ED2_ROOT="${ED2_ROOT:-${repo_root}}"
ED2_SIF="${ED2_SIF:-${ED2_ROOT}/containers/ed2-intel.sif}"
ED2_INPUT_DEFAULT="${ED2_INPUT:-.ED2IN-default}"

default_threads="$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 1)"
ED2_THREADS="${ED2_THREADS:-${OMP_NUM_THREADS:-${default_threads}}}"

resolved_inputs=()
used_default_run=false
if [[ $# -eq 0 ]]; then
   resolved_inputs+=("${ED2_INPUT_DEFAULT}")
   used_default_run=true
else
   for arg in "$@"; do
      if [[ -f "${arg}" ]]; then
         resolved_inputs+=("$(basename "${arg}")")
         continue
      fi

      if [[ "${arg}" == *[\*\?\[]* ]]; then
         matches=( ${config_dir}/${arg} )
         if [[ ${#matches[@]} -gt 0 && "${matches[0]}" != "${config_dir}/${arg}" ]]; then
            for match in "${matches[@]}"; do
               [[ -f "${match}" ]] && resolved_inputs+=("$(basename "${match}")")
            done
            continue
         fi
      fi

      if [[ -f "${config_dir}/${arg}" ]]; then
         resolved_inputs+=("${arg}")
      else
         echo "Missing ED2 namelist in ${config_dir}: ${arg}" >&2
         exit 2
      fi
   done
fi

if ${used_default_run}; then
   default_message="DEFAULT RUN: QUICK SMOKE CHECK WITH ${ED2_INPUT_DEFAULT}"
   printf -v default_rule '%*s' "${#default_message}" ''
   default_rule="${default_rule// /#}"
   echo "${default_rule}" >&2
   echo "${default_message}" >&2
   echo "${default_rule}" >&2
fi

if [[ ! -d "${config_dir}" ]]; then
   echo "Missing ED2 run directory: ${config_dir}" >&2
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

prepare_output_dirs() {
   local ed2_input="$1"
   local prefix output_dir

   while IFS= read -r prefix; do
      [[ -n "${prefix}" ]] || continue
      output_dir="$(dirname "${prefix}")"
      mkdir -p "${output_dir}"
   done < <(sed -n -E "s/^[[:space:]]*NL%(FFILOUT|SFILOUT)[[:space:]]*=[[:space:]]*['\"]([^'\"]+)['\"].*/\2/p" "${config_dir}/${ed2_input}")
}

announce_run_list() {
   local ed2_input

   echo "Namelists to run (${#resolved_inputs[@]}):"
   for ed2_input in "${resolved_inputs[@]}"; do
      echo "  - ${ed2_input}"
   done
}

export OMP_NUM_THREADS="${ED2_THREADS}"
export APPTAINERENV_OMP_NUM_THREADS="${OMP_NUM_THREADS}"
export SINGULARITYENV_OMP_NUM_THREADS="${OMP_NUM_THREADS}"

echo "ED2 root:       ${ED2_ROOT}"
echo "Run directory:  ${config_dir}"
echo "SIF image:      ${ED2_SIF}"
echo "Container:      ${container_cmd}"
echo "OMP threads:    ${OMP_NUM_THREADS}"
echo "Stack before:   $(ulimit -s)"
announce_run_list

cd "${config_dir}"
ulimit -s unlimited
echo "Stack after:    $(ulimit -s)"

for ed2_input in "${resolved_inputs[@]}"; do
   if [[ ! -s "${config_dir}/${ed2_input}" ]]; then
      echo "Missing ED2 namelist: ${config_dir}/${ed2_input}" >&2
      exit 2
   fi

   prepare_output_dirs "${ed2_input}"

   echo "Namelist:       ${ed2_input}"
   "${container_cmd}" exec       --bind "${ED2_ROOT}:${ED2_ROOT}"       "${ED2_SIF}"       bash -lc "cd '${config_dir}' && ulimit -s unlimited && exec ed2 -f '${ed2_input}'"
done
