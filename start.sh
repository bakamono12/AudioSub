#!/bin/bash
set -e  # Exit immediately if a command fails

# Create directories
mkdir -p /tmp/bin

# Show current directory and files
echo "Current directory: $(pwd)"
echo "Listing files:"
ls -la

# Download static FFmpeg build with error handling
echo "Downloading static FFmpeg..."
wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz -O /tmp/ffmpeg.tar.xz
if [ $? -ne 0 ]; then
  echo "Failed to download FFmpeg, trying alternative URL..."
  wget https://github.com/eugeneware/ffmpeg-static/releases/download/b4.4.0/linux-x64 -O /tmp/bin/ffmpeg
  chmod +x /tmp/bin/ffmpeg
else
  echo "Extracting FFmpeg..."
  tar -xf /tmp/ffmpeg.tar.xz -C /tmp
  # Find the extracted directory and copy binaries
  find /tmp -name "ffmpeg" -type f -exec cp {} /tmp/bin/ \;
  find /tmp -name "ffprobe" -type f -exec cp {} /tmp/bin/ \;
  chmod +x /tmp/bin/ffmpeg /tmp/bin/ffprobe
fi

# Add to PATH and make it available to subprocesses
export PATH="/tmp/bin:$PATH"
echo "PATH=$PATH" >> ~/.bashrc
echo "export PATH" >> ~/.bashrc

# Verify FFmpeg installation
echo "FFmpeg path: $(which ffmpeg || echo 'NOT FOUND')"
if [ -f /tmp/bin/ffmpeg ]; then
  echo "FFmpeg exists at /tmp/bin/ffmpeg"
  ls -la /tmp/bin/ffmpeg
  /tmp/bin/ffmpeg -version || echo "Failed to run ffmpeg"
else
  echo "FFmpeg binary not found at /tmp/bin/ffmpeg!"
fi

# Create symbolic links in /usr/local/bin as fallback
sudo ln -sf /tmp/bin/ffmpeg /usr/local/bin/ffmpeg || echo "Failed to create symlink in /usr/local/bin"
sudo ln -sf /tmp/bin/ffprobe /usr/local/bin/ffprobe || echo "Failed to create symlink in /usr/local/bin"

# Modify your app.py or main.py to use full path to ffmpeg
sed -i 's/subprocess.run\(\["ffmpeg"/subprocess.run(["\\/tmp\\/bin\\/ffmpeg"/g' main.py || echo "Failed to modify main.py"
sed -i 's/subprocess.run\(\["ffmpeg"/subprocess.run(["\\/tmp\\/bin\\/ffmpeg"/g' celery_worker.py || echo "Failed to modify celery_worker.py"

# Start the application with the updated PATH
echo "Starting application..."
export PATH="/tmp/bin:$PATH"
exec gunicorn main:app