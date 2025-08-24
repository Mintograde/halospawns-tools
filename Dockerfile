FROM public.ecr.aws/lambda/python:3.10 AS builder

ARG BLENDER_MAJOR_MINOR="2.93"
ARG BLENDER_VERSION="${BLENDER_MAJOR_MINOR}.0"
ARG AETHER_REPO="Mintograde/AetherCLI"
ARG AETHER_TAG="v1.0.8"
ARG AETHER_ASSET_NAME="AetherCLI-${AETHER_TAG}-linux-x64.zip"

# NOTE: downloading standalone python to work around tkinter issues in the base image (required for reclaimer/refinery)
#       https://github.com/aws/aws-lambda-base-images/tree/python3.10
#       https://github.com/aws/aws-lambda-base-images/issues/70
#       https://github.com/aws/aws-lambda-python-runtime-interface-client/issues/90
#       https://github.com/open-mmlab/mmdetection/issues/9403
#       https://stackoverflow.com/questions/74473315/unable-to-import-module-app-no-module-named-tkinter-errortype-runtim
ARG PYTHON_VERSION="3.10.18"
ARG PYTHON_BUILD_URL="https://github.com/astral-sh/python-build-standalone/releases/download/20250814/cpython-${PYTHON_VERSION}+20250814-x86_64-unknown-linux-gnu-install_only.tar.gz"

RUN yum install -y wget unzip tar gzip xz curl jq

WORKDIR /build

RUN wget -O python.tar.gz ${PYTHON_BUILD_URL} && \
    mkdir /opt/python && \
    tar -xzf python.tar.gz -C /opt/python --strip-components=1

RUN wget https://dot.net/v1/dotnet-install.sh -O dotnet-install.sh && \
    chmod +x ./dotnet-install.sh && \
    ./dotnet-install.sh --version latest --runtime aspnetcore --install-dir /opt/dotnet

RUN wget https://download.blender.org/release/Blender${BLENDER_MAJOR_MINOR}/blender-${BLENDER_VERSION}-linux-x64.tar.xz && \
    mkdir blender && \
    tar -xvf blender-${BLENDER_VERSION}-linux-x64.tar.xz --strip-components=1 -C blender

RUN --mount=type=secret,id=github_pat \
    echo "Fetching release info for tag ${AETHER_TAG} from repo ${AETHER_REPO}..." && \
    ASSET_URL=$(curl --fail --location \
        --header "Authorization: token $(cat /run/secrets/github_pat)" \
        --header "Accept: application/vnd.github.v3+json" \
        "https://api.github.com/repos/${AETHER_REPO}/releases/tags/${AETHER_TAG}" | \
        jq -r ".assets[] | select(.name == \"${AETHER_ASSET_NAME}\") | .url") && \
    if [ -z "$ASSET_URL" ]; then \
        echo "ERROR: Could not find asset URL for ${ASSET_NAME}." >&2; exit 1; \
    fi && \
    echo "Downloading asset from ${ASSET_URL}..." && \
    curl --fail --location --output "${AETHER_ASSET_NAME}" \
        --header "Authorization: token $(cat /run/secrets/github_pat)" \
        --header "Accept: application/octet-stream" \
        "${ASSET_URL}" && \
    echo "Unpacking asset..." && \
    unzip "${AETHER_ASSET_NAME}" -d "AetherCLI" && rm "${AETHER_ASSET_NAME}"


FROM public.ecr.aws/lambda/python:3.10

WORKDIR ${LAMBDA_TASK_ROOT}

COPY --from=builder /opt/python /opt/python
COPY --from=builder /opt/dotnet /opt/dotnet
COPY --from=builder /build/blender ${LAMBDA_TASK_ROOT}/blender
COPY --from=builder /build/AetherCLI ${LAMBDA_TASK_ROOT}/AetherCLI

ENV DOTNET_ROOT=/opt/dotnet \
    AETHER_EXECUTABLE_PATH=${LAMBDA_TASK_ROOT}/AetherCLI/AetherCLI \
    BLENDER_EXECUTABLE_PATH=${LAMBDA_TASK_ROOT}/blender/blender \
    CE_PATH=/tmp/ce \
    PATH="/opt/python/bin:${LAMBDA_TASK_ROOT}:${LAMBDA_TASK_ROOT}/blender:${DOTNET_ROOT}:${PATH}" \
    CC=gcc \
    PYTHONPATH=/opt/python/bin

COPY convert_map.py \
     map_to_scenario.py \
     obj_cleanup.py \
     blender.py \
     blender_293.py \
     scenario_to_obj.py \
     app.py \
     requirements.txt \
     ./

# use downloaded standalone python instead of built in python
RUN ln -sf /opt/python/bin/python /var/lang/bin/python &&  \
    ls -sf /opt/python/bin/python /var/lang/bin/python3.10 && \
    ln -sf /opt/python/bin/pip /var/lang/bin/pip && \
    sed -i 's|/var/lang/bin/python3.10|/opt/python/bin/python|g' /var/runtime/bootstrap

RUN yum install -y \
        gcc gcc-c++ make \
        libX11 libXext libXrender libXi libXxf86vm libICE libSM mesa-libGL && \
    pip install -r requirements.txt && \
    yum remove -y gcc gcc-c++ make && \
    yum clean all && \
    rm -rf /var/cache/yum

# patch reclaimer to remove excessive warnings from lambda logs
RUN sed -i '/print("Ignore me if you/,/print(format_exc())$/d' /opt/python/lib/python3.10/site-packages/reclaimer/hek/handler.py && \
    sed -i '/Animation tag missing nodes/,/their gbxmodel in 3DS Max/d' /opt/python/lib/python3.10/site-packages/reclaimer/animation/animation_decompilation.py

CMD [ "app.handler" ]