#!/bin/bash
# set -e

component_kmd=0
component_umd=0
checkdeb=0
summary=0 
component=0
branch=0
commitID=0
oss_url="https://oss.mthreads.com"
# commit_type_kmd=0
# commit_type_umd=0
# install_kmd_flag=0
# install_umd_flag=0

# ./download_driver.py -c umd -b develop -i 0d610f8ad
# modules=(pvrsrvkm mtgpu_kms mtgpu)
modules=(mtgpu)
# files_dir=(etc lib usr)
#remove kmd modules

function net_check() {
	ip_addr=$(ip addr |grep inet|grep -vE "docker0|wl|\<lo"|grep "192.168"|awk '{print $2}'|awk -F/ '{print $1}')
	if [ $ip_addr != "127.0.0.1" ];then 
		echo $ip_addr
	else
		echo "[INFO] ip=$ip_addr,未检测到DHCP分配ip"
		exit 1
	fi
	test_ip=$(echo $oss_url |awk -F "https://" '{print $NF}')
    # test_ip="www.baidu.com"
    echo $test_ip
	#检查是否有网络
	ping_result=$(ping -c1 -W1 $test_ip >> ping.txt 2>&1)
	#ping一次，超时时间1秒，ping的通返回0，echo up，ping失败打印down
	if [ $? -eq 0 ]
	then   
    	echo "[INFO] 可以ping通$test_ip"
	else
    	echo "[ERROR] 无法ping通$test_ip"
    	exit 1
	fi
}

function download_all() {
    echo download_all
    # deb_version=$1
    # deb_url="${oss_url}/product-release/${branch}/${work_date}/${driver_name}"
}

function download_kmd() {
    commitID=$1
    # kmd_url=oss/release-ci/gr-kmd/develop/${commitID}_1050u3_uos_arm64-mtgpu_linux-xorg-release-hw.tar.gz
    #KMD更换地址后 2023-12-18之后
    kmd_url="${oss_url}/sw-build/gr-kmd/${branch}/${commitID}/${commitID}_${arch}-mtgpu_linux-xorg-release-hw.tar.gz"
    # dkms_kmd_deb_url="${oss_url}/${commitID}/${commitID}_${arch}-mtgpu_linux-xorg-release-hw.deb"
    echo "[INFO] Downloading KMD_${commitID}.tar.gz"
    wget $kmd_url -O KMD_${commitID}.tar.gz
    if [ $? -ne 0 ];then 
        echo -e "[INFO] $kmd_url download failed! \n[INFO] Please check whether $kmd_url is there!"
        exit 1
    fi
    mkdir KMD_$commitID && tar -xvf KMD_${commitID}.tar.gz -C "KMD_${commitID}/"
    KMD_tar_kernel=$(find KMD_${commitID}/ -name mtgpu.ko |awk -F/ '{print $(NF-2)}')
    if [[ $KMD_tar_kernel != $(uname -r) ]];then
        echo -e "[INFO] KMD_${commitID}.tar.gz内核${KMD_tar_kernel}与系统内核$(uname -r)不匹配;\n[INFO] Download dkms KMD_${commitID}.deb"
        kmd_url="${oss_url}/sw-build/gr-kmd/${branch}/${commitID}/${commitID}_${arch}-mtgpu_linux-xorg-release-hw.deb"
        wget $kmd_url -O KMD_${commitID}.deb
        rm -rf KMD_${commitID}.tar.gz
    fi
    echo "[INFO] Download KMD_${commitID} complete"
}

function download_umd() {
    commitID=$1
    umd_url="${oss_url}/release-ci/gr-umd/${branch}/${commitID}_${arch}-mtgpu_linux-xorg-release-hw${glvnd}.tar.gz"
    echo "[INFO] Download  UMD_${commitID}"
    wget $umd_url -O UMD_${commitID}${glvnd}.tar.gz
    if [ $? -ne 0 ];then 
        echo -e "[INFO] $umd_url download failed! \n[INFO] Please check whether oss/release-ci/gr-umd/${branch}/${commitID}_${arch}-mtgpu_linux-xorg-release-hw${glvnd}.tar.gz is there!"
        exit 1
    fi
    mkdir UMD_$commitID && tar -xvf UMD_${commitID}${glvnd}.tar.gz -C UMD_${commitID}
    echo "[INFO] Download  UMD_${commitID} complete"
}

# 安装KMD
function install_kmd() {
    echo "[INFO] Start install KMD"
    # sudo rmmod mtgpu
    commitID=$1
    sudo rmmod mtgpu
    # sudo modprobe -rv mtgpu
    #下载的KMD内核版本与系统内核版本一致就直接替换安装，否则使用dkms deb安装
    if [ -e KMD_${commitID}.tar.gz ];
    then 
        echo "[INFO] 直接替换KMD"
        if [ -e "/lib/modules/`uname -r`/updates/dkms/mtgpu.ko" ];then 
            sudo mv /lib/modules/`uname -r`/updates/dkms/mtgpu.ko /lib/modules/`uname -r`/updates/dkms/mtgpu.ko.bak
        fi
        sudo mkdir -p /lib/modules/`uname -r`/extra/
        # sudo modprobe -rv mtgpu
        sudo cp $(find KMD_${commitID}/${arch}-mtgpu_linux-xorg-release/ -name mtgpu.ko) /lib/modules/`uname -r`/extra/
        # sudo depmod
        # sudo update-initramfs -u -k `uname -r`
    else
        echo "[INFO] 安装dkms mtgpu deb, 请确保musa驱动已卸载"
        echo "[INFO] 安装KMD mtgpu dkms deb失败...musa包与kmd dkms deb mtgpu包冲突，需卸载musa包"
        # show_umd_info
        dpkg -s musa
        if [ $? != 1 ];then
            echo "[INFO] sudo dpkg -P musa"
            sudo dpkg -P musa;
            sudo rm -rf /usr/lib/$(uname -m)-linux-gnu/musa
            echo "[INFO] musa all in one deb卸载完成"
        fi
        # check_umd_install 
        if [ ! -d /usr/lib/$(uname -m)-linux-gnu/musa ] ;then
            echo "UMD musa package is not installed;" 
            read -p "请输入要安装的UMD commitID:" umd_commit
                if [[ $umd_commit == '' ]];then
                    echo "[ERROR] You need install UMD package before install KMD!"
                    exit 1
                fi
            download_umd  $umd_commit && install_umd $umd_commit
        fi
        commitID=$1
        echo "[INFO] sudo dpkg -i ${run_path}/KMD_${commitID}.deb "
        sudo dpkg -i ${run_path}/KMD_${commitID}.deb 

    fi
    if [ ! -e /etc/modprobe.d/mtgpu.conf ];then 
        # wget -q --no-check-certificate https://oss.mthreads.com/product-release/cts/mtgpu_perf.conf -O mtgpu.conf && sudo cp mtgpu.conf /etc/modprobe.d
        echo -e "options mtgpu display=mt EnableFWContextSwitch=27"  |sudo tee /etc/modprobe.d/mtgpu.conf
    fi
    # 重启机器
    read -p "kmd安装完成，是否要重启机器？[yY/nN]: " answer
    case $answer in 
    Y | y)
        echo "重启机器"
        sleep 2
        sudo depmod -a
        sudo update-initramfs -u -k `uname -r`
        sudo reboot
        ;;
    N | n)
        echo "执行modprobe -v mtgpu"
        sudo rmmod mtgpu
        if [ $? = 0 ];then 
            sudo depmod 
            sudo modprobe -v mtgpu      
        fi
        ;;
    *)
        echo "input error!"
        ;;
    esac
    echo "[INFO] KMD install complete"
}



#安装umd
function install_umd() {
    echo "[INFO] Start install UMD"
    # sudo systemctl stop lightdm
    commitID=$1
    cd UMD_${commitID}/${arch}-mtgpu_linux-xorg-release/
    echo "[INFO] install UMD..."
    if [[ $glvnd == "-glvnd" ]];then 
        #glvnd umd安装方式
        #卸载UMD
        sudo ./install.sh -g -n -u .
        #安装UMD
        sudo ./install.sh -g -n -s .
    else
        #非glvnd umd安装方式
        # 指向/usr/local/bin/Xorg （非glvnd UMD包安装路径）
        sudo sed -i 's/lib\/xorg/local\/bin/g' /usr/bin/X
        #卸载UMD
        sudo ./install.sh -u .
        #安装UMD
        sudo ./install.sh -s .
    fi
    if [[ ! -e /etc/ld.so.conf.d/00-mtgpu.conf ]];then
        # echo "/usr/lib/$arch-linux-gnu/musa" > /etc/ld.so.conf.d/00-mtgpu.conf
        echo -e "/usr/lib/$(uname -m)-linux-gnu/musa" |sudo tee /etc/ld.so.conf.d/00-mtgpu.conf
        if [[ "$(uname -m)" == "aarch64" ]]; then
            # echo "/usr/lib/arm-linux-gnueabihf/musa" >> /etc/ld.so.conf.d/00-mtgpu.conf
            echo -e "/usr/lib/arm-linux-gnueabihf/musa" |sudo tee -a /etc/ld.so.conf.d/00-mtgpu.conf
        fi
    fi
    sudo ldconfig
    echo "[INFO] UMD install complete"
}

function show_deb_info() {
    # echo "show_deb_info"
    FenGeLine "DEB INFO"
    musa_info=$(dpkg -s musa  musa_all_in_one 2>/dev/null|grep Version |awk -F: '{print $NF}')
    mtgpu_info=$(dpkg -s mtgpu  2>/dev/null|grep Version |awk -F: '{print $NF}')
    if [[ $musa_info == '' ]] && [[ $mtgpu_info == '' ]];then   
        echo "[INFO] run 'dpkg -s musa musa_all_in_one mtgpu' failed! Please check musa deb is installed."
    elif [[ $musa_info != '' ]];then
        echo "[INFO] dpkg -s musa"
        dpkg -s musa 
    elif [[ $mtgpu_info != '' ]];then
        echo "[INFO] dpkg -s mtgpu"
        dpkg -s mtgpu
    else 
        echo "[ERROR] musa、mtgpu cannot install at the same time; Please check musa or mtgpu install status." 
    fi
    echo 
}

function FenGeLine() {
    str="="
    # ScreenLen=$(stty size |awk '{print $2}')
    ScreenLen=80
    TitleLen=$(echo -n $1 |wc -c)
    LineLen=$(((${ScreenLen} - ${TitleLen}) / 2 ))
    yes $str |sed ''''${LineLen}'''q' |tr -d "\n" && echo -n $1 && yes $str |sed ''''${LineLen}'''q' |tr -d "\n" && echo
}
function show_kmd_info() {
    #echo "KMD INFO"
    FenGeLine "KMD INFO"
    for m in ${modules[@]}
    do 
        if lsmod |grep "$m" > /dev/null 2>&1 
        then 
            echo "[INFO] $m loaded"
            # kmd_commit=$(grep "MTGPU Driver Version" /var/log/kern.log |tail -n 1 |awk -F: '{print $NF}' |awk '{print $1}')
            kmd_commit=$(sudo grep "Driver Version" /sys/kernel/debug/musa/version|awk -F[ '{print $NF}'|awk -F] '{print $1}')
            # kmd commit 只显示7位；检查安装成功时只能对比前7位字母数字；
            echo "[INFO] KMD commitID : $kmd_commit"
        else
            echo "[ERROR] $m not loaded, Please run 'sudo lsmod |grep mtgpu' to check mtgpu.ko is loaded!"
            exit 1
            
        fi
    done
    echo 
}

function show_umd_info() {
#    echo "shwo umd info "
    FenGeLine "UMD INFO"
    umd_commit=$(export DISPLAY=:0.0 && glxinfo -B |grep -i "OpenGL version string"|awk '{print $NF}'|awk -F "@" '{print $1}')
    # umd_commit=$(clinfo |grep "Driver Version"|awk -F' '  '{print $6}'|awk -F'@' '{print $1}')
    if [[ $umd_commit != "" ]]
    then
        echo "[INFO] UMD commitID : $umd_commit"
    else
        echo "[ERROR] 无法查询到umd info, please check Xorg status;"
    fi
    echo 
}



function usage() {
    # echo in usage
    # 实现效果：检查出当前环境的commit，包括kmd和umd；安装指定commitID的kmd或umd；
    # $0 -s | [-c all|kmd|umd ] -b branch [-i commitID ] |-h 
    echo "Usage: $0 -s | -b <daily/release/master/haiguang/kylin> -c <all|kmd|umd>  -i commitID | -h"
    echo "
-s      # show driver info summary,include KMD/UMD COMMIT INFO;
-b      # --branch  <develop/release/master/haiguang/kylin>
-c      # component deb/kmd/umd ;
-i      # umd/kmd merge commit;
-h      # --help"
     
}

function parse_args() {
    while getopts :sb:c:i:h option
    do 
        case "$option" in
            s)
                # echo "-s"
                summary=1
                ;;
            b) 
                branch=$OPTARG
                ;;
            c)
                if [ "$OPTARG" = "kmd" ];
                then 
                    component='kmd'
                elif [ "$OPTARG" = "umd" ];
                then 
                    component='umd'
                elif [ "$OPTARG" = "all" ]    
                then
                    component='all'
                else
                    usage
                    exit 1
                fi
                ;;
            i)
                commitID=$OPTARG
                ;;
            h)
                usage
                exit 0 
                ;;
            # *) 
            #     echo "[Error] Illegal option -${option}"
            #     usage
            #     ;;
            :)
                echo "选项-$OPTARG后面需要一个参数值"
                usage
                exit 1
                ;;
            ?)
                echo "Unknown args -$OPTARG!"
                usage
                exit 1
                ;; 
        esac

        
    done

    if [ $# -eq 0 ]
    then 
        echo "缺少参数"
        usage
        exit 1
    fi
}
function main() {
    # echo in main
    parse_args "$@"
    if [ $summary -eq 1 ];then 
        show_deb_info
        show_kmd_info
        show_umd_info
        exit 0
    else    
        if [[ $component == '0' ]] || [[ $branch == '0' ]]
        then
            echo "You need set component and branch!"
            usage
            exit 1
        elif [ $component = 'all' ];then 
            commitID=''
        else
            commitID=$commitID
            if [ $commitID = '0' ];then 
                echo "You need input a commitID!"
                usage
                exit 1
            fi
        fi
        net_check
        echo "[INFO] sudo systemctl stop lightdm"
        sudo systemctl stop lightdm
        download_${component} $commitID
        install_${component} $commitID
        echo "[INFO] sudo systemctl restart lightdm"
        sudo systemctl restart lightdm
    fi
    
    
}

run_path=$(pwd)
os_type=$(cat /etc/os-release |grep 'NAME'|grep -v "PRETTY_NAME"|grep -v  "CODENAME"|awk -F\" '{print $(NF-1)}')
arch=$(uname -m)
if [ $arch = 'aarch64' ];then 
   arch='arm64'
fi
glvnd="-glvnd"
# os是Kylin就使用非glvnd的umd；
# if [ $os_type = "Kylin" ];then 
#     glvnd=''
# fi
 
main "$@"


    
