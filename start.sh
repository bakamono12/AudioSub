#!/bin/bash
set -e  # Exit immediately if a command fails

# Create directories
mkdir -p /tmp/bin
mkdir -p uploads
mkdir -p results

# Show current directory and files
echo "Current directory: $(pwd)"
echo "Listing files:"
ls -la

# Install wget and curl if needed
echo "Installing system tools..."
apt-get update && apt-get install -y curl wget ffmpeg || echo "Failed to install with apt-get"

# Try using curl instead of wget
echo "Downloading static FFmpeg..."
if command -v curl &> /dev/null; then
    curl -L https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz -o /tmp/ffmpeg.tar.xz

    if [ $? -eq 0 ]; then
        echo "Extracting FFmpeg..."
        tar -xf /tmp/ffmpeg.tar.xz -C /tmp
        # Find the extracted directory
        FFMPEG_DIR=$(find /tmp -type d -name "ffmpeg-*-amd64-static" | head -n 1)
        if [ -n "$FFMPEG_DIR" ]; then
            cp $FFMPEG_DIR/ffmpeg /tmp/bin/
            cp $FFMPEG_DIR/ffprobe /tmp/bin/
            chmod +x /tmp/bin/ffmpeg /tmp/bin/ffprobe
            echo "FFmpeg copied to /tmp/bin"
        else
            echo "FFmpeg directory not found after extraction"
        fi
    else
        echo "Failed to download FFmpeg"
    fi
else
    echo "curl command not found, trying direct system install"
    apt-get update && apt-get install -y ffmpeg
fi

# Add to PATH
export PATH="/tmp/bin:$PATH"
echo "PATH=$PATH"

# Create symlinks in multiple locations for redundancy
ln -sf /tmp/bin/ffmpeg /usr/local/bin/ffmpeg || echo "Failed to create symlink in /usr/local/bin"
ln -sf /tmp/bin/ffmpeg /usr/bin/ffmpeg || echo "Failed to create symlink in /usr/bin"

# Verify FFmpeg installation - try multiple locations
echo "Checking FFmpeg locations:"
if [ -f /tmp/bin/ffmpeg ]; then
    echo "FFmpeg exists at /tmp/bin/ffmpeg"
    /tmp/bin/ffmpeg -version || echo "Failed to run /tmp/bin/ffmpeg"
elif [ -f /usr/local/bin/ffmpeg ]; then
    echo "FFmpeg exists at /usr/local/bin/ffmpeg"
    /usr/local/bin/ffmpeg -version || echo "Failed to run /usr/local/bin/ffmpeg"
elif [ -f /usr/bin/ffmpeg ]; then
    echo "FFmpeg exists at /usr/bin/ffmpeg"
    /usr/bin/ffmpeg -version || echo "Failed to run /usr/bin/ffmpeg"
else
    echo "FFmpeg not found in any location!"
    # Last resort: try installing ffmpeg directly
    apt-get update && apt-get install -y ffmpeg
    which ffmpeg || echo "FFmpeg not found in PATH after install"
fi

# Start the application
echo "Starting application..."
exec gunicorn main:app