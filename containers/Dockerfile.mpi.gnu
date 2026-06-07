# ----------------------------------------------------------------------
# Build MPI-enabled ED2 model
# ----------------------------------------------------------------------
FROM ubuntu:22.04 AS build

ARG ED2_KIND=E

ENV FC_TYPE=GNU \
    ED2_KIND=${ED2_KIND} \
    TZ=America/Chicago \
    DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
       gfortran \
       openmpi-bin \
       libopenmpi-dev \
       libhdf5-openmpi-dev \
       libblas-dev \
       liblapack-dev \
    && rm -rf /var/lib/apt/lists/*

COPY ED       /ED2/ED
COPY RAPP     /ED2/RAPP
COPY Ramspost /ED2/Ramspost

WORKDIR /ED2/ED/build
RUN ./install.sh -k ${ED2_KIND} -g -p docker.mpi.gnu
RUN if [ -e ed_*-opt ]; then mv ed_*-opt ed2; else mv ed_*-dbg ed2; fi

########################################################################

# ----------------------------------------------------------------------
# Runtime image with ED2 and OpenMPI
# ----------------------------------------------------------------------
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       bash \
       openmpi-bin \
       libopenmpi3 \
       libhdf5-openmpi-103 \
       libblas3 \
       liblapack3 \
       libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /data
COPY --from=build /ED2/ED/build/ed2 /usr/bin

CMD ["/usr/bin/ed2"]
