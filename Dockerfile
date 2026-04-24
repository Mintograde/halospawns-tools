FROM python:3.14-slim AS builder

ARG BLENDER_MAJOR_MINOR="2.93"
ARG BLENDER_VERSION="${BLENDER_MAJOR_MINOR}.0"
ARG AETHER_REPO="Mintograde/AetherCLI"
ARG AETHER_TAG="v1.0.8"
ARG AETHER_ASSET_NAME="AetherCLI-${AETHER_TAG}-linux-x64.zip"
ARG AETHER_ASSET_URL="https://github.com/${AETHER_REPO}/releases/download/${AETHER_TAG}/${AETHER_ASSET_NAME}"
ARG DOTNET_CHANNEL="8.0"

RUN apt-get update && \
    apt-get install -y --no-install-recommends wget unzip tar gzip xz-utils jq findutils ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /build

RUN wget https://dot.net/v1/dotnet-install.sh -O dotnet-install.sh && \
    chmod +x ./dotnet-install.sh && \
    ./dotnet-install.sh --version latest --channel ${DOTNET_CHANNEL} --runtime aspnetcore --install-dir /opt/dotnet

RUN wget https://download.blender.org/release/Blender${BLENDER_MAJOR_MINOR}/blender-${BLENDER_VERSION}-linux-x64.tar.xz && \
    mkdir blender && \
    tar -xvf blender-${BLENDER_VERSION}-linux-x64.tar.xz --strip-components=1 -C blender

RUN wget -O ${AETHER_ASSET_NAME} ${AETHER_ASSET_URL} && \
    unzip "${AETHER_ASSET_NAME}" -d "AetherCLI" && rm "${AETHER_ASSET_NAME}"


FROM python:3.14-slim

WORKDIR /var/task

COPY --from=builder /opt/dotnet /opt/dotnet
COPY --from=builder /build/blender /var/task/blender
COPY --from=builder /build/AetherCLI /var/task/AetherCLI

ENV DOTNET_ROOT=/opt/dotnet
ENV AETHER_EXECUTABLE_PATH=/var/task/AetherCLI/AetherCLI \
    BLENDER_EXECUTABLE_PATH=/var/task/blender/blender \
    CE_PATH=/tmp/ce \
    PATH="/var/task:/var/task/blender:${DOTNET_ROOT}:${PATH}" \
    CC=gcc

COPY convert_map.py \
     map_to_scenario.py \
     obj_cleanup.py \
     blender.py \
     blender_293.py \
     scenario_to_obj.py \
     app.py \
     requirements.txt \
     patch_reclaimer.py \
     ./

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        g++ libicu-dev \
        libx11-6 libxext6 libxrender1 libxi6 libxxf86vm1 libice6 libsm6 libgl1 libxfixes3 \
        tcl tk && \
    pip install -r requirements.txt && \
    python patch_reclaimer.py /usr/local/lib/python3.14/site-packages && \
    rm -rf /var/lib/apt/lists/*

ENTRYPOINT ["/usr/local/bin/python", "-m", "awslambdaric"]
CMD [ "app.handler" ]
