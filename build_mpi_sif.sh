#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
dockerfile="${ED2_MPI_DOCKERFILE:-${script_dir}/Dockerfile.mpi.intel}"
image_name="${ED2_MPI_DOCKER_IMAGE:-ed2-mpi-intel:latest}"
sif_path="${ED2_MPI_SIF:-${script_dir}/ed2-mpi-intel.sif}"

if ! command -v docker >/dev/null 2>&1; then
   echo "docker is not available in PATH." >&2
   exit 127
fi

if ! command -v apptainer >/dev/null 2>&1; then
   echo "apptainer is not available in PATH." >&2
   exit 127
fi

echo "Building Docker image: ${image_name}"
docker build -f "${dockerfile}" -t "${image_name}" "${script_dir}"

echo "Building SIF image: ${sif_path}"
apptainer build "${sif_path}" "docker-daemon://${image_name}"

echo "Wrote ${sif_path}"
