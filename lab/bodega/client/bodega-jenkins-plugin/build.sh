#!/bin/bash

GRADLE_VERSION=4.7
GRADLE_PATH=/home/ubuntu/gradle-$GRADLE_VERSION/bin/gradle
GRADLE_DOWNLOAD_URL=https://repo.corp.rubrik.com/nexus/repository/misc/stark/build_tools/gradle/gradle-$GRADLE_VERSION-bin.zip

GRADLE_PROJECT_PATH=$1

if [ ! -f $GRADLE_PATH ]; then
    echo "Gradle not found"
    echo "Downloading gradle from $GRADLE_DOWNLOAD_URL"
    wget $GRADLE_DOWNLOAD_URL -O /tmp/gradle.zip
    echo "Extracting gradle in /home/ubuntu"
    unzip /tmp/gradle.zip -d /home/ubuntu
    rm /tmp/gradle.zip
fi

$GRADLE_PATH jpi -p $GRADLE_PROJECT_PATH
