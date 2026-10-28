#!/bin/bash
set -e
echo "tlm setup"

sudo apt-get update -qq
sudo apt-get install -y -qq cmake build-essential python3-pip git wget
pip3 install Pillow --break-system-packages 2>/dev/null || pip3 install Pillow

if [ ! -d "llama.cpp" ]; then
  wget -q "https://api.github.com/repos/ggml-org/llama.cpp/tarball/v1.0.0" -O /tmp/llama.tar.gz
  tar xzf /tmp/llama.tar.gz
  mv ggml-org-llama.cpp-* llama.cpp
  rm /tmp/llama.tar.gz
fi

cd llama.cpp
cmake -B build \
  -DCMAKE_BUILD_TYPE=MinSizeRel \
  -DGGML_NATIVE=OFF -DGGML_CPU_AARCH64=ON -DLLAMA_CURL=OFF \
  -DBUILD_SHARED_LIBS=OFF \
  -DGGML_VULKAN=OFF -DGGML_METAL=OFF -DGGML_CUDA=OFF \
  -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=OFF -DLLAMA_BUILD_SERVER=OFF
cmake --build build --config MinSizeRel -j4 --target llama-completion
cp build/bin/llama-completion ../
cd ..

./download_model.sh
echo "done. test: python3 tlm.py 'what is the sun'"
