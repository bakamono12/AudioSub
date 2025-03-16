#!/bin/bash

# Download static FFmpeg build (doesn't depend on system libraries)
echo "Downloading static FFmpeg..."
curl -L https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz -o ffmpeg.tar.xz
tar xf ffmpeg.tar.xz
mkdir -p /tmp/bin
cp ffmpeg-*-amd64-static/ffmpeg /tmp/bin/
cp ffmpeg-*-amd64-static/ffprobe /tmp/bin/
export PATH="/tmp/bin:$PATH"
echo "FFmpeg installed to /tmp/bin"

# Verify FFmpeg works
ffmpeg -version

# Start the application
gunicorn app:app