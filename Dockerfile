FROM python:3.14-slim

# Install dependencies for osslsigncode and smart card support
RUN apt-get update && apt-get install -y \
    libengine-pkcs11-openssl \
    libpcsclite1 \
    opensc \
    osslsigncode \
    pcscd \
    pcsc-tools \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Download and install Certum proCertumCardManager as we need the pkcs#11 module
RUN cd /tmp \
    && wget https://files.certum.eu/software/proCertumCardManager/Linux-Ubuntu/2.2.15/proCertumCardManager-2.2.15-x86_64-ubuntu.bin \
    && chmod +x proCertumCardManager-2.2.15-x86_64-ubuntu.bin \
    && mkdir certum-extract \
    && cd certum-extract \
    && ../proCertumCardManager-2.2.15-x86_64-ubuntu.bin --tar xvf \
    && mkdir -p /opt/proCertumCardManager \
    && cp -r * /opt/proCertumCardManager/ \
    && cd /tmp \
    && rm -rf certum-extract proCertumCardManager-2.2.15-x86_64-ubuntu.bin

# Download and install ACS ACR40T driver for smart card reader support.
# The generic libccid package seems to support the ACS ACR40T OK.
RUN apt-get update && apt-get install -y libccid

# Install python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application files
COPY signer.py .
COPY signing_cert.pem /certs/signing_cert.pem
COPY https_cert.pem /certs/https_cert.pem
COPY https_key.pem /certs/https_key.pem

CMD ["uvicorn", "signer:app", "--host", "0.0.0.0", "--port", "8443", "--log-level", "info", "--ssl-keyfile", "/certs/https_key.pem", "--ssl-certfile", "/certs/https_cert.pem"]