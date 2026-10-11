#!/usr/bin/env bash
set -euo pipefail
mkdir -p build/ffmpeg build/sources
curl --fail --location --retry 3 https://codeload.github.com/FFmpeg/FFmpeg/tar.gz/refs/tags/n8.0 -o build/sources/ffmpeg-n8.0.tar.gz
echo 'dd4030dbfdc34d9ff255a116bdd1caade42500ac2981efa27f8b151cc54c7b9e  build/sources/ffmpeg-n8.0.tar.gz' | sha256sum --check
tar -xzf build/sources/ffmpeg-n8.0.tar.gz -C build
cd build/FFmpeg-n8.0
./configure --target-os=mingw32 --arch=x86_64 --disable-autodetect --disable-network \
  --disable-doc --disable-debug --disable-ffplay --disable-ffprobe --disable-shared \
  --enable-static --disable-x86asm --extra-ldflags=-static
make -j2
cp ffmpeg.exe ../ffmpeg/ffmpeg.exe
cp COPYING.LGPLv2.1 ../ffmpeg/LICENSE.txt
./ffmpeg.exe -version > ../ffmpeg/build-configuration.txt
