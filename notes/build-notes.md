# building llama.cpp for pi zero

native build takes ~45min. cross compile from pi 5 faster since same arch.

build flags:
  cmake -B build \
    -DCMAKE_BUILD_TYPE=MinSizeRel \
    -DGGML_NATIVE=OFF \
    -DGGML_CPU_AARCH64=ON \
    -DLLAMA_CURL=OFF \
    -DBUILD_SHARED_LIBS=OFF \
    -DGGML_VULKAN=OFF -DGGML_METAL=OFF -DGGML_CUDA=OFF \
    -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=OFF -DLLAMA_BUILD_SERVER=OFF

only build llama-completion target. 8mb static binary.

256 context max practical. 512 works but tight. 1024 OOMs.
