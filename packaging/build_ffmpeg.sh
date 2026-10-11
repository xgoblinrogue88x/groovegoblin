#!/usr/bin/env bash
set -euo pipefail
mkdir -p build/ffmpeg build/sources
curl --fail --location --retry 3 https://codeload.github.com/FFmpeg/FFmpeg/tar.gz/refs/tags/n8.0 -o build/sources/ffmpeg-n8.0.tar.gz
echo 'dd4030dbfdc34d9ff255a116bdd1caade42500ac2981efa27f8b151cc54c7b9e  build/sources/ffmpeg-n8.0.tar.gz' | sha256sum --check
tar -xzf build/sources/ffmpeg-n8.0.tar.gz -C build
cd build/FFmpeg-n8.0
./configure --target-os=mingw32 --arch=x86_64 --disable-autodetect --disable-network \
  --disable-doc --disable-debug --disable-ffplay --disable-ffprobe --disable-shared --disable-iconv \
  --enable-static --disable-x86asm --extra-ldflags=-static \
  --disable-everything --enable-protocol=file,pipe \
  --enable-demuxer=aac,aiff,ape,asf,dsf,iff,flac,mp3,mov,ogg,wav,wv,pcm_u8,pcm_s16le,pcm_s16be,pcm_s24le,pcm_s24be,pcm_s32le,pcm_s32be,pcm_f32le,pcm_f32be \
  --enable-decoder=aac,aac_fixed,alac,ape,flac,mp3,mp3float,opus,vorbis,wavpack,wmav1,wmav2,wmapro,wmalossless,wmavoice,dst,dsd_lsbf,dsd_msbf,dsd_lsbf_planar,dsd_msbf_planar,pcm_s8,pcm_u8,pcm_s16le,pcm_s16be,pcm_s24le,pcm_s24be,pcm_s32le,pcm_s32be,pcm_f32le,pcm_f32be,pcm_f64le,pcm_f64be,pcm_alaw,pcm_mulaw \
  --enable-encoder=pcm_s16le,flac --enable-muxer=wav,flac \
  --enable-parser=aac,aac_latm,flac,mpegaudio,opus,vorbis \
  --enable-filter=aresample,aformat,anull,sine --enable-indev=lavfi
make -j4
cp ffmpeg.exe ../ffmpeg/ffmpeg.exe
cp COPYING.LGPLv2.1 ../ffmpeg/LICENSE.txt
./ffmpeg.exe -version > ../ffmpeg/build-configuration.txt
