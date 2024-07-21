#!/usr/bin/env bash
set -e
function init_common() {
    sudo apt install libvulkan-dev -y
    sudo apt install libassimp-dev -y
}
#VulkanDemos-BoblChen
function install_VulkanDemos-BoblChen() {
    cd  $project_path/VulkanSample/VulkanDemos-BoblChen/
    if [[ $arch == 'aarch64' ]];then
        wget http://192.168.114.118/tool/UE/sample/src/sse2neon.h
        sudo cp sse2neon.h /usr/include/
        sudo mv sse2neon.h /usr/local/include/
        sed -i "s|emmintrin.h|sse2neon.h|g" Engine/Monkey/Loader/stb_image.h
        sed -i "s|emmintrin.h|sse2neon.h|g" examples/72_MeshLOD/vertexfilter.cpp
        sed -i "s|emmintrin.h|sse2neon.h|g" external/assimp/contrib/stb_image/stb_image.h
        sed -i "s|emmintrin.h|sse2neon.h|g" external/assimp/contrib/rapidjson/include/rapidjson/writer.h
        sed -i "s|emmintrin.h|sse2neon.h|g" external/assimp/contrib/rapidjson/include/rapidjson/reader.h
        sed -i "s|xmmintrin.h|sse2neon.h|g" Engine/Monkey/Math/Linux/LinuxPlatformMath.h
    fi
    cmake -S . -B build
    cmake --build build
}

#vulkan-basic-samples
function install_vulkan-basic-samples() {
    cd  $project_path/VulkanSample/vulkan-basic-samples/
    sudo apt install spirv-tools -y
    sudo apt-get install git build-essential libx11-xcb-dev \
        libxkbcommon-dev libwayland-dev libxrandr-dev -y
    cp ./API-Samples/android/ShaderHeaders/spirv_assembly.vert.h API-Samples/spirv_assembly.vert.h
    mkdir build 
    cd build
    cmake -DCMAKE_BUILD_TYPE=Debug \
            -DVULKAN_HEADERS_INSTALL_DIR=absolute_path_to_install_dir \
            -DVULKAN_LOADER_INSTALL_DIR=absolute_path_to_install_dir \
            -DCMAKE_INSTALL_PREFIX=install ..
    if [[ $arch == 'aarch64' ]];then
        wget http://192.168.114.118/tool/UE/sample/src/glslang
        cp glslang ../glslang/bin/glslangValidator
        cp glslang ../glslang/bin/
    fi
    make -j4    
}

#Khronos-Vulkan-Samples
function install_Khronos-Vulkan-Samples() {
    cd  $project_path/VulkanSample/Khronos-Vulkan-Samples/
    sudo apt install cmake g++ xorg-dev libglu1-mesa-dev -y
    cmake -G "Unix Makefiles" -Bbuild/linux -DCMAKE_BUILD_TYPE=Release
    cmake --build build/linux --config Release --target vulkan_samples -j8
    # cmake -S . -B build/linux -DCMAKE_BUILD_TYPE=Debug
    # cmake --build build/linux --config Debug --target vulkan_samples -j32
    # cp -rf shaders/ ./build/linux/app/bin/Debug/x86_64/
    # cp -rf assets/  ./build/linux/app/bin/Debug/x86_64/
    cp -rf shaders/ ./build/linux/app/bin/Release/$arch
    cp -rf assets/ ./build/linux/app/bin/Release/$arch
}

#Vulkan-glTF-PBR
function install_Vulkan-glTF-PBR() {
    cd  $project_path/VulkanSample/Vulkan-glTF-PBR/
    cmake .
    make
}

#SaschaWillems-Vulkan
function install_SaschaWillems-Vulkan() {
    cd  $project_path/VulkanSample/SaschaWillems-Vulkan/
    sudo apt-get install libglm-dev -y
    cmake -S . -B build
    cmake --build build
}

function help_info() {
    echo "support project: VulkanDemos-BoblChen、vulkan-basic-samples、Khronos-Vulkan-Samples、Vulkan-glTF-PBR、SaschaWillems-Vulkan"
    echo "默认安装所有vulkan samples"
    echo "执行\"$0 < VulkanDemos-BoblChen / vulkan-basic-samples / Khronos-Vulkan-Samples / Vulkan-glTF-PBR / SaschaWillems-Vulkan >\"可单独安装"
}

project=$1
wget http://192.168.114.118/tool/UE/sample/VulkanSample.mt.tar.gz 
arch=`uname -m`
export project_path=`pwd`
tar -xvf $project_path/VulkanSample.mt.tar.gz 
init_common
if [[ $project == '-h' ]] || [[ $project == '--help' ]]
then 
    help_info
elif [[ $project == '' ]];then 
    help_info
    install_VulkanDemos-BoblChen
    install_vulkan-basic-samples
    install_Khronos-Vulkan-Samples
    install_Vulkan-glTF-PBR
    install_SaschaWillems-Vulkan
else
    install_${project}
fi

