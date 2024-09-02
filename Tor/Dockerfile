# Use a specific Alpine Linux version as the base image for reproducibility
FROM alpine:3.18

# Install necessary packages and create a non-root user for security
RUN apk update && apk add --no-cache tor bash

# Copy custom Tor configuration if needed
COPY torrc /etc/tor/torrc

# Expose the port Tor uses for DNS (comment out if not needed)
EXPOSE 9053

# Set the user to the non-root user
USER tor

# Add a health check to ensure Tor is running
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD nc -zv localhost 9050 || exit 1

# Run Tor
CMD ["tor"]
