FROM public.ecr.aws/lambda/python:3.14 AS builder

ARG BLENDER_MAJOR_MINOR="2.93"
ARG BLENDER_VERSION="${BLENDER_MAJOR_MINOR}.0"
ARG AETHER_REPO="Mintograde/AetherCLI"
ARG AETHER_TAG="v1.0.8"
ARG AETHER_ASSET_NAME="AetherCLI-${AETHER_TAG}-linux-x64.zip"
ARG AETHER_ASSET_URL="https://github.com/${AETHER_REPO}/releases/download/${AETHER_TAG}/${AETHER_ASSET_NAME}"
ARG DOTNET_CHANNEL="8.0"

# NOTE: downloading standalone python to work around tkinter issues in the base image (required for reclaimer/refinery)
#       https://github.com/aws/aws-lambda-base-images/tree/python3.10
#       https://github.com/aws/aws-lambda-base-images/issues/70
#       https://github.com/aws/aws-lambda-python-runtime-interface-client/issues/90
#       https://github.com/open-mmlab/mmdetection/issues/9403
#       https://stackoverflow.com/questions/74473315/unable-to-import-module-app-no-module-named-tkinter-errortype-runtim
ARG PYTHON_VERSION="3.14.4"
ARG PYTHON_TAG="20260408"
ARG PYTHON_BUILD_URL="https://github.com/astral-sh/python-build-standalone/releases/download/${PYTHON_TAG}/cpython-${PYTHON_VERSION}+${PYTHON_TAG}-x86_64-unknown-linux-gnu-install_only.tar.gz"

RUN dnf install -y wget unzip tar gzip xz jq findutils

WORKDIR /build

RUN wget -O python.tar.gz ${PYTHON_BUILD_URL} && \
    mkdir /opt/python && \
    tar -xzf python.tar.gz -C /opt/python --strip-components=1

RUN wget https://dot.net/v1/dotnet-install.sh -O dotnet-install.sh && \
    chmod +x ./dotnet-install.sh && \
    ./dotnet-install.sh --version latest --channel ${DOTNET_CHANNEL} --runtime aspnetcore --install-dir /opt/dotnet

RUN wget https://download.blender.org/release/Blender${BLENDER_MAJOR_MINOR}/blender-${BLENDER_VERSION}-linux-x64.tar.xz && \
    mkdir blender && \
    tar -xvf blender-${BLENDER_VERSION}-linux-x64.tar.xz --strip-components=1 -C blender

RUN wget -O ${AETHER_ASSET_NAME} ${AETHER_ASSET_URL} && \
    unzip "${AETHER_ASSET_NAME}" -d "AetherCLI" && rm "${AETHER_ASSET_NAME}"


FROM public.ecr.aws/lambda/python:3.14

WORKDIR ${LAMBDA_TASK_ROOT}

COPY --from=builder /opt/python /opt/python
COPY --from=builder /opt/dotnet /opt/dotnet
COPY --from=builder /build/blender ${LAMBDA_TASK_ROOT}/blender
COPY --from=builder /build/AetherCLI ${LAMBDA_TASK_ROOT}/AetherCLI

ENV DOTNET_ROOT=/opt/dotnet
ENV AETHER_EXECUTABLE_PATH=${LAMBDA_TASK_ROOT}/AetherCLI/AetherCLI \
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
     patch_reclaimer.py \
     ./

# use downloaded standalone python instead of built in python
RUN ln -sf /opt/python/bin/python /var/lang/bin/python &&  \
    ls -sf /opt/python/bin/python /var/lang/bin/python3.14 && \
    ln -sf /opt/python/bin/pip /var/lang/bin/pip && \
    sed -i 's|/var/lang/bin/python3.14|/opt/python/bin/python|g' /var/runtime/bootstrap

RUN dnf install -y \
        gcc-c++ libicu \
        libX11 libXext libXrender libXi libXxf86vm libICE libSM mesa-libGL && \
    pip install -r requirements.txt && \
    python patch_reclaimer.py /opt/python/lib/python3.14/site-packages && \
    dnf clean all && \
    rm -rf /var/cache/dnf && \
    rm -rf /var/yum/dnf

CMD [ "app.handler" ]