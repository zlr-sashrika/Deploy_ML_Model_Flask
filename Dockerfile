FROM python:3.12-alpine AS builder

# Set environment variables for CLI tools
ENV KUBECTL_VERSION="v1.28.0" \
    HELM_VERSION="v3.12.3" \
    ARGOCD_VERSION="v2.9.4" \
    GCLOUD_SDK_VERSION="509.0.0" \
    # AWS_CLI_VERSION="2.24.11" \
    BUILD_BASE="/build-tools" \
    POETRY_HOME="/opt/poetry" \
    POETRY_VERSION=1.7.1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1 \
    PATH="/opt/poetry/bin:$PATH"

# Install build dependencies
RUN apk add --no-cache \
    python3 \
    py3-pip \
    make \
    g++ \
    bash \
    gcc \
    musl-dev \
    python3-dev \
    libffi-dev \
    openssl-dev \
    cargo \
    curl

# Install Poetry using the official installer
RUN curl -sSL https://install.python-poetry.org | python3 - 

# Set up poetry environment
WORKDIR /app
COPY pyproject.toml ./

# Install dependencies
RUN poetry install --no-interaction --no-ansi --no-root
COPY . .
RUN pyinstaller --onefile app.py --distpath devops_agent/bin/.dist/ --specpath devops_agent/bin/ --workpath devops_agent/bin/.build/ --hidden-import=pydantic.deprecated.decorator --hidden-import=tiktoken_ext.openai_public --hidden-import=tiktoken_ext

FROM python:3.12-alpine

# Copy Python packages and Poetry environment from builder
COPY --from=builder /usr/local /usr/local
COPY --from=builder /usr/lib /usr/lib
COPY --from=builder /app/devops_agent/bin/.dist/app /usr/local/bin/app

# Copy RAG data
RUN mkdir -p /usr/local/share/devopsgpt/rag/data
COPY --from=builder /app/devops_agent/rag/data /usr/local/share/devopsgpt/rag/data
RUN chmod -R 775 /usr/local/share/devopsgpt/

# Set environment variables for CLI tools
ENV KUBECTL_VERSION="v1.28.0" \
    HELM_VERSION="v3.12.3" \
    ARGOCD_VERSION="v2.9.4" \
    GCLOUD_SDK_VERSION="509.0.0" \
    # AWS_CLI_VERSION="2.24.11" \
    PATH="/opt/poetry/bin:$PATH"

# Install runtime dependencies and CLI tools
RUN apk add --no-cache \
    bash \
    curl \
    wget \
    tar \
    git \
    buildah \
    netavark aardvark-dns slirp4netns \
    ca-certificates \
    libffi \
    libstdc++ && \
    # Install kubectl
    curl -LO "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl" && \
    install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl && \
    # Install Helm
    curl -LO "https://get.helm.sh/helm-${HELM_VERSION}-linux-amd64.tar.gz" && \
    tar -zxvf helm-${HELM_VERSION}-linux-amd64.tar.gz && \
    mv linux-amd64/helm /usr/local/bin/helm && \
    rm -rf linux-amd64 helm-${HELM_VERSION}-linux-amd64.tar.gz && \
    # Install ArgoCD CLI
    curl -sSL -o /usr/local/bin/argocd "https://github.com/argoproj/argo-cd/releases/download/${ARGOCD_VERSION}/argocd-linux-amd64" && \
    chmod +x /usr/local/bin/argocd && \
    # Install Google Cloud SDK
    curl -sSL https://sdk.cloud.google.com > /tmp/install.sh && \
    bash /tmp/install.sh --disable-prompts --install-dir=/usr/local && \
    rm -f /tmp/install.sh && \
    # TODO: Install Specific AWS CLI
    # curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64-${AWS_CLI_VERSION}.zip" -o "awscliv2.zip" && \
    # unzip awscliv2.zip && \
    # ./aws/install && \
    # rm -rf aws awscliv2.zip && \
    # Create docker CLI alias using buildah
    ln -s /usr/bin/buildah /usr/local/bin/docker && \
    # Clean up
    apk del tar && \
    rm -rf /var/cache/apk/*
RUN apk add --no-cache aws-cli


ENV PATH="/usr/local/google-cloud-sdk/bin:$PATH"
ENV PATH="/usr/local/bin:$PATH"
WORKDIR /app
#COPY . .

# Set the default command
ENTRYPOINT ["/usr/local/bin/app"]
#CMD ["app.py"] 
