# Use Alpine Linux as the base image
FROM alpine:latest

# Install necessary packages
RUN apk update && \
    apk add --no-cache tor

# Copy custom Tor configuration if needed
COPY torrc /etc/tor/torrc

# Expose the port Tor uses for DNS
#EXPOSE 9053

# Run Tor
CMD ["tor"]
