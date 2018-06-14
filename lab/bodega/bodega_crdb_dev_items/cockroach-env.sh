#!/bin/bash
NEW_DISK_DIR="/data"
COCKROACH_DIR="$NEW_DISK_DIR/go/src/github.com/cockroachdb/cockroach"
ROACHPROD_DIR="$NEW_DISK_DIR/go/src/github.com/cockroachdb/roachprod"
DOWNLOAD_DIR="/root/Downloads"
GO_TAR="go1.10.linux-amd64.tar.gz"
DOCKER_VER="18.03.0~ce-0~ubuntu"

mkdir $NEW_DISK_DIR

# install go 1.10
# go is needed for running builder.sh.
wget -P $DOWNLOAD_DIR "https://dl.google.com/go/$GO_TAR"
tar -C /usr/local -xzf $DOWNLOAD_DIR/$GO_TAR
export PATH=$PATH:/usr/local/go/bin
export GOPATH=$NEW_DISK_DIR/go

# install git
apt-get update
apt-get install -y --force-yes git

# install docker, detailed explanation of each step is in
# https://docs.docker.com/install/linux/docker-ce/ubuntu
apt-get update
apt-get install -y apt-transport-https ca-certificates curl \
software-properties-common
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -
add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
$(lsb_release -cs) stable"
apt-get update
apt-get install -y docker-ce=$DOCKER_VER
