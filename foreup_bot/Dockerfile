FROM public.ecr.aws/amazonlinux/amazonlinux:2023

# Install Python 3.11 and Lambda runtime
RUN dnf update -y && dnf install -y \
    python3.11 \
    python3.11-pip \
    python3.11-devel \
    gcc \
    && dnf clean all

# Install Lambda runtime interface
RUN pip3.11 install awslambdaric

# Set up Lambda environment
ENV LAMBDA_TASK_ROOT=/var/task
ENV LAMBDA_RUNTIME_DIR=/var/runtime
WORKDIR ${LAMBDA_TASK_ROOT}

# Install system dependencies for Playwright (manual installation)
RUN dnf install -y \
    wget \
    unzip \
    fontconfig \
    libXcomposite \
    libXcursor \
    libXdamage \
    libXext \
    libXi \
    libXtst \
    cups-libs \
    libXScrnSaver \
    libXrandr \
    alsa-lib \
    pango \
    atk \
    at-spi2-atk \
    gtk3 \
    nss \
    freetype \
    freetype-devel \
    fontconfig-devel \
    libstdc++ \
    glib2 \
    glib2-devel \
    && dnf clean all

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip3.11 install -r requirements.txt

# Install Playwright browsers (skip dependency installation)
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
RUN playwright install chromium

# Copy function code
COPY aws/lambda_handler_playwright.py ${LAMBDA_TASK_ROOT}
COPY monitoring/ ${LAMBDA_TASK_ROOT}/monitoring/
COPY config/ ${LAMBDA_TASK_ROOT}/config/

# Set the CMD to your handler
CMD [ "/usr/bin/python3.11", "-m", "awslambdaric", "lambda_handler_playwright.lambda_handler" ] 