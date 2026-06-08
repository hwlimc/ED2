#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd "${script_dir}/.." && pwd)"
repo_root="$(cd "${project_root}/../.." && pwd)"
config_dir="${ED2_RUN_DIR:-${project_root}/config}"

ED2_ROOT="${ED2_ROOT:-${repo_root}}"
ED2_SIF="${ED2_SIF:-${ED2_ROOT}/containers/ed2-mpi-intel.sif}"
ED2_INPUT_DEFAULT="${ED2_INPUT:-.ED2IN-default-mpi}"

if [[ $# -gt 0 && "${1}" =~ ^[0-9]+$ ]]; then
   ED2_MPI_RANKS="${1}"
   shift
elif [[ $# -gt 1 && "${!#}" =~ ^[0-9]+$ ]]; then
   ED2_MPI_RANKS="${!#}"
   set -- "${@:1:$(($# - 1))}"
elif [[ $# -gt 0 ]]; then
   ED2_MPI_RANKS="${ED2_MPI_RANKS:-4}"
else
   ED2_MPI_RANKS="${ED2_MPI_RANKS:-4}"
fi

I_MPI_PIN="${I_MPI_PIN:-0}"
ED2_THREADS="${ED2_THREADS:-1}"

if [[ ! "${ED2_MPI_RANKS}" =~ ^[1-9][0-9]*$ ]]; then
   echo "MPI ranks must be a positive integer: ${ED2_MPI_RANKS}" >&2
   exit 2
fi

if [[ ! -d "${config_dir}" ]]; then
   echo "Missing ED2 run directory: ${config_dir}" >&2
   exit 2
fi

if [[ ! -s "${ED2_SIF}" ]]; then
   echo "Missing MPI Apptainer image: ${ED2_SIF}" >&2
   echo "Build it first with: ${ED2_ROOT}/scripts/build_mpi_sif.sh" >&2
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

resolve_inputs() {
   local arg match found

   if [[ $# -eq 0 ]]; then
      resolved_inputs+=("${ED2_INPUT_DEFAULT}")
      used_default_run=true
      return
   fi

   for arg in "$@"; do
      if [[ -f "${arg}" ]]; then
         resolved_inputs+=("$(basename "${arg}")")
         continue
      fi

      if [[ "${arg}" == *[\*\?\[]* ]]; then
         found=false
         while IFS= read -r match; do
            [[ -f "${match}" ]] || continue
            resolved_inputs+=("$(basename "${match}")")
            found=true
         done < <(compgen -G "${config_dir}/${arg}" | sort)

         if ${found}; then
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
}

validate_inputs() {
   local ed2_input n_poi

   for ed2_input in "${resolved_inputs[@]}"; do
      if [[ ! -s "${config_dir}/${ed2_input}" ]]; then
         echo "Missing ED2 namelist: ${config_dir}/${ed2_input}" >&2
         exit 2
      fi

      n_poi="$(sed -n -E 's/^[[:space:]]*NL%N_POI[[:space:]]*=[[:space:]]*(-?[0-9]+).*/\1/p' "${config_dir}/${ed2_input}" | tail -n 1)"
      if [[ "${ED2_MPI_RANKS}" -gt 1 && -n "${n_poi}" && "${n_poi}" -gt 0 ]]; then
         echo "MPI ranks > 1 cannot run POI namelist ${ed2_input} (NL%N_POI=${n_poi})." >&2
         echo "Use a regional namelist with NL%N_POI=0, or run this case with serial run_ed2.sh." >&2
         exit 2
      fi
   done
}

announce_default_run() {
   local default_message default_rule

   default_message="DEFAULT RUN: QUICK SMOKE CHECK WITH ${ED2_INPUT_DEFAULT}"
   printf -v default_rule '%*s' "${#default_message}" ''
   default_rule="${default_rule// /#}"

   echo "${default_rule}"
   echo "${default_message}"
   echo "${default_rule}"
}

announce_run_list() {
   local ed2_input line_width max_len=0

   for ed2_input in "${resolved_inputs[@]}"; do
      if [[ ${#ed2_input} -gt ${max_len} ]]; then
         max_len=${#ed2_input}
      fi
   done

   line_width=$((max_len + 21))
   printf -v line '%*s' "${line_width}" ''
   line="${line// /#}"

   echo "${line}"
   echo "NAMELISTS TO RUN (${#resolved_inputs[@]})"
   for ed2_input in "${resolved_inputs[@]}"; do
      echo "  - ${ed2_input}"
   done
   echo "${line}"
}

resolved_inputs=()
used_default_run=false
resolve_inputs "$@"
validate_inputs

export OMP_NUM_THREADS="${ED2_THREADS}"
export APPTAINERENV_OMP_NUM_THREADS="${OMP_NUM_THREADS}"
export SINGULARITYENV_OMP_NUM_THREADS="${OMP_NUM_THREADS}"
export APPTAINERENV_I_MPI_PIN="${I_MPI_PIN}"
export SINGULARITYENV_I_MPI_PIN="${I_MPI_PIN}"

if ${used_default_run}; then
   announce_default_run
fi

echo "ED2 root:       ${ED2_ROOT}"
echo "Run directory:  ${config_dir}"
echo "MPI SIF image:  ${ED2_SIF}"
echo "Container:      ${container_cmd}"
echo "MPI ranks:      ${ED2_MPI_RANKS}"
echo "OMP threads:    ${OMP_NUM_THREADS}"
echo "Intel MPI pin:  ${I_MPI_PIN}"
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

   if [[ ${#resolved_inputs[@]} -gt 1 ]]; then
      echo "========================================================================="
      echo "Running ${ed2_input} with ${ED2_MPI_RANKS} MPI ranks"
      echo "========================================================================="
   else
      echo "Namelist:       ${ed2_input}"
   fi

   prepare_output_dirs "${ed2_input}"

   "${container_cmd}" exec    --bind "${ED2_ROOT}:${ED2_ROOT}"    "${ED2_SIF}"    bash -lc "cd '${config_dir}' && ulimit -s unlimited && export OMP_NUM_THREADS='${OMP_NUM_THREADS}' I_MPI_PIN='${I_MPI_PIN}' && exec mpirun -np '${ED2_MPI_RANKS}' ed2 -f '${ed2_input}'"
done
