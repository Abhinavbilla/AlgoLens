#!/bin/sh
# One-time setup of a fresh Ubuntu 24.04 server for AlgoLens (run with sudo).
set -eu

# Docker Engine with the Compose plugin, from Docker's own repository.
if ! command -v docker >/dev/null 2>&1; then
    apt-get update -q
    apt-get install -yq ca-certificates curl git
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    chmod a+r /etc/apt/keyrings/docker.asc
    . /etc/os-release
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $VERSION_CODENAME stable" \
        > /etc/apt/sources.list.d/docker.list
    apt-get update -q
    apt-get install -yq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi
usermod -aG docker "${SUDO_USER:-azureuser}"

# nsjail (the code sandbox) needs unprivileged user namespaces, which Ubuntu 24.04 restricts
# through AppArmor by default. Keep it allowed across reboots.
echo "kernel.apparmor_restrict_unprivileged_userns=0" > /etc/sysctl.d/60-algolens-userns.conf
sysctl -q --system

# Swap as a safety net for image builds and C++ compiles on a small machine.
if [ ! -f /swapfile ]; then
    fallocate -l 4G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile >/dev/null
    swapon /swapfile
    echo "/swapfile none swap sw 0 0" >> /etc/fstab
fi

# Automatic security updates.
apt-get install -yq unattended-upgrades >/dev/null
echo "setup done"
