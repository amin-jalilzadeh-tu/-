# Dockerfile
FROM python:3.9-slim

WORKDIR /usr/src/app

# --- System packages we need ---
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    wget \
    unzip \
    tk \
    tcl \
    && rm -rf /var/lib/apt/lists/*

# (1) Copy the requirements files
COPY requirements_base.txt .
COPY requirements_dev.txt .

# (2) Install base (large) deps
RUN pip install --no-cache-dir -r requirements_base.txt

# (3) Install dev (smaller) deps
RUN pip install --no-cache-dir -r requirements_dev.txt

# (4) Download & Install EnergyPlus 22.2.0
#     (Adjust link to exact version / tarball you want)
RUN wget "https://github.com/NREL/EnergyPlus/releases/download/v22.2.0/EnergyPlus-22.2.0-c249759bad-Linux-Ubuntu20.04-x86_64.tar.gz" \
    && tar -xzvf "EnergyPlus-22.2.0-c249759bad-Linux-Ubuntu20.04-x86_64.tar.gz" \
    && rm "EnergyPlus-22.2.0-c249759bad-Linux-Ubuntu20.04-x86_64.tar.gz" \
    # rename the extracted directory
    && mv EnergyPlus-22.2.0-c249759bad-Linux-Ubuntu20.04-x86_64 EnergyPlus-22-2-0 \
    # now create a symlink from /usr/local/EnergyPlus-22-2-0 -> /usr/src/app/EnergyPlus-22-2-0
    && ln -s /usr/src/app/EnergyPlus-22-2-0 /usr/local/EnergyPlus-22-2-0 \
    # create a symlink for the binary
    && ln -s /usr/local/EnergyPlus-22-2-0/energyplus /usr/local/bin/energyplus


# (5) Copy your entire project LAST (so changes to code won't break caching of the above steps)
COPY . .

# (6) Expose port & default command
EXPOSE 8000
CMD ["gunicorn", "-b", "0.0.0.0:8000", "app:app", "--workers=1", "--timeout=600"]
