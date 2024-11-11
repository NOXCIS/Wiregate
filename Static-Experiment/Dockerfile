# Stage 1: Build stage
FROM python:3.12-alpine AS builder

# Install required build dependencies
RUN apk add --no-cache \
    py3-virtualenv \
    py3-pip \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev

WORKDIR /build

# Copy application code and dependencies
COPY dashboard.py .
COPY requirements.txt .

# Set up a virtual environment and install dependencies
RUN python3 -m venv venv \
    && source venv/bin/activate \
    && pip install --upgrade pip \
    && pip install -r requirements.txt

# Use PyInstaller to create a standalone binary
RUN source venv/bin/activate \
    && pip install pyinstaller \
    && pyinstaller --onefile --name dashboard dashboard.py

# Stage 2: Final image
FROM alpine:latest
EXPOSE 8080
# Create directory for the binary
WORKDIR /WireGate

# Copy the compiled binary from the builder stage
COPY --from=builder /build/dist/dashboard /WireGate/dashboard
COPY ./dist /WireGate/
RUN mkdir -p /etc/wireguard

# Set executable permission
RUN chmod +x /WireGate/dashboard

# Run the binary by default
CMD ["/WireGate/dashboard"]
