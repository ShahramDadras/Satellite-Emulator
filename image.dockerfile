
# Use the latest Ubuntu image shahramdd/sat:2.0
FROM ubuntu:22.04

# Install necessary tools
RUN apt update && apt install -y iputils-ping iproute2 net-tools sudo tcpdump

# Keep the container running
CMD ["tail", "-f", "/dev/null"]


`````````````````````````````````````````````````````````````````````````````````````````````````````````````````````
# Use the latest Alpine image
FROM alpine:latest

# Install necessary tools
RUN apk add --no-cache iputils iproute2 net-tools sudo tcpdump

# Keep the container running
CMD ["tail", "-f", "/dev/null"]

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~    

# Use the latest Ubuntu image shahramdd/sat:3.1
# Use the latest Ubuntu image
FROM ubuntu:22.04

# Install necessary tools
RUN apt update && apt install -y iputils-ping iproute2 net-tools sudo tcpdump bridge-utils

# Add a script to create bridges
COPY create_bridges.sh /usr/local/bin/create_bridges.sh
RUN chmod +x /usr/local/bin/create_bridges.sh

# Keep the container running and create the bridges
CMD ["/usr/local/bin/create_bridges.sh"]
========================================================================================================================================
shahramdd/sat:3.2

FROM ubuntu:22.04

# Install essential tools, editors, dependencies, and FRRouting
RUN apt update && apt install -y iputils-ping iproute2 net-tools sudo tcpdump bridge-utils nano vim curl gnupg lsb-release ca-certificates && \
    curl -s https://deb.frrouting.org/frr/keys.asc | gpg --dearmor -o /etc/apt/trusted.gpg.d/frr.gpg && \
    echo "deb https://deb.frrouting.org/frr $(lsb_release -cs) frr-stable" > /etc/apt/sources.list.d/frr.list && \
    apt update && apt install -y frr frr-pythontools

# Copy your bridge creation script
COPY create_bridges.sh /usr/local/bin/create_bridges.sh
RUN chmod +x /usr/local/bin/create_bridges.sh

# Set working directory (optional)
# WORKDIR /etc/frr

# Run your bridge setup script
CMD ["/usr/local/bin/create_bridges.sh"]

====================================================================================================================================================
# shahramdd/sat:3.3
FROM ubuntu:22.04

# Install essential tools, editors, dependencies, and FRRouting
RUN apt update && apt install -y iputils-ping iproute2 net-tools sudo tcpdump bridge-utils nano vim curl gnupg lsb-release ca-certificates && \
    curl -s https://deb.frrouting.org/frr/keys.asc | gpg --dearmor -o /etc/apt/trusted.gpg.d/frr.gpg && \
    echo "deb https://deb.frrouting.org/frr $(lsb_release -cs) frr-stable" > /etc/apt/sources.list.d/frr.list && \
    apt update && apt install -y frr frr-pythontools

# Ensure that frr service can be controlled in container
RUN ln -s /etc/init.d/frr /usr/bin/service

# Copy your bridge creation script
COPY create_bridges.sh /usr/local/bin/create_bridges.sh
RUN chmod +x /usr/local/bin/create_bridges.sh

# Set working directory (optional)
# WORKDIR /etc/frr

# Run your bridge setup script
CMD ["/usr/local/bin/create_bridges.sh"]

=====================================================================================================================
# shahramdd/sat:3.3
FROM ubuntu:22.04

# Install essential tools, editors, dependencies, and FRRouting
RUN apt update && apt install -y iputils-ping iproute2 net-tools sudo tcpdump bridge-utils nano vim curl gnupg lsb-release ca-certificates && \
    curl -s https://deb.frrouting.org/frr/keys.asc | gpg --dearmor -o /etc/apt/trusted.gpg.d/frr.gpg && \
    echo "deb https://deb.frrouting.org/frr $(lsb_release -cs) frr-stable" > /etc/apt/sources.list.d/frr.list && \
    apt update && apt install -y frr frr-pythontools

# Ensure that frr service can be controlled in container
RUN ln -s /etc/init.d/frr /usr/bin/service

# Copy your bridge creation script
COPY create_bridges.sh /usr/local/bin/create_bridges.sh
RUN chmod +x /usr/local/bin/create_bridges.sh

# Set working directory (optional)
# WORKDIR /etc/frr

# Run your bridge setup script
CMD ["/usr/local/bin/create_bridges.sh"]
========================================================================================================================
# shahramdd/sat:3.4
FROM ubuntu:22.04

RUN apt update && apt install -y iputils-ping iproute2 net-tools sudo tcpdump bridge-utils nano vim curl gnupg lsb-release ca-certificates && \
    curl -s https://deb.frrouting.org/frr/keys.asc | gpg --dearmor -o /etc/apt/trusted.gpg.d/frr.gpg && \
    echo "deb https://deb.frrouting.org/frr $(lsb_release -cs) frr-stable" > /etc/apt/sources.list.d/frr.list && \
    apt update && apt install -y frr frr-pythontools && \
    apt install -y iperf3

RUN ln -s /etc/init.d/frr /usr/bin/service

COPY create_bridges.sh /usr/local/bin/create_bridges.sh
RUN chmod +x /usr/local/bin/create_bridges.sh

CMD ["/usr/local/bin/create_bridges.sh"]






















