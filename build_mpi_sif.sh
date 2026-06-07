#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
dockerfile="${ED2_MPI_DOCKERFILE:-${script_dir}/Dockerfile.mpi.intel}"
image_name="${ED2_MPI_DOCKER_IMAGE:-ed2-mpi-intel:latest}"
sif_path="${ED2_MPI_SIF:-${script_dir}/ed2-mpi-intel.sif}"
mksquashfs_args="${ED2_MPI_MKSQUASHFS_ARGS:--processors 1}"

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
if [[ -n "${mksquashfs_args}" ]]; then
   echo "Apptainer mksquashfs args: ${mksquashfs_args}"
   apptainer build --force --mksquashfs-args "${mksquashfs_args}" "${sif_path}" "docker-daemon://${image_name}"
else
   apptainer build --force "${sif_path}" "docker-daemon://${image_name}"
fi

echo "Wrote ${sif_path}"
