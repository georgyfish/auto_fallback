#!/usr/bin/python3
# import get_commit
import os,sys,time,re
from get_deb_version import get_deb_version
import subprocess
import get_commit
import umd_fallback
from datetime import datetime
from sshClient import sshClient
from logManager import logManager
import test


# driver_dic = {'20240326': ['musa_2024.03.26-D+10129', 'https://oss.mthreads.com/release-ci/repo_tags/20240326.txt', 'https://oss.mthreads.com/product-release/develop/20240326/musa_2024.03.26-D+10129+dkms+glvnd-Ubuntu_amd64.deb', 'musa_2024.03.26-D+10129+dkms+glvnd-Ubuntu_amd64.deb'], '20240327': ['musa_2024.03.27-D+10151', 'https://oss.mthreads.com/release-ci/repo_tags/20240327.txt', 'https://oss.mthreads.com/product-release/develop/20240327/musa_2024.03.27-D+10151+dkms+glvnd-Ubuntu_amd64.deb', 'musa_2024.03.27-D+10151+dkms+glvnd-Ubuntu_amd64.deb']}
# lis1 = ["commit0","commit1","commit2","commit3","commit4","commit5","commit6","commit7","commit8","commit9","commit10","commit11","commit12"]
# dic1 = {"commit0":"true","commit1":"true","commit2":"true","commit3":"true","commit4":"true","commit5":"true","commit6":"true","commit7":"true","commit8":"true","commit9":"true","commit10":"true","commit11":"true","commit12":"true"}fd

def get_Pc_info(Pc):
    VALID_OS_TYPE = {"Kylin", "Ubuntu", "uos"}
    VALID_OS_ARCH_MAP = {"x86_64": "amd64", "aarch64": "arm64", "loongarch64": "loongarch64"}
    result = {}
    commands = {
    "os_type": "cat /etc/lsb-release | head -n 1 | awk -F '='  '{print $2}'",
    "architecture": "dpkg --print-architecture",
    "arch":"uname -m" ,
    # "lspci": "lspci",
    "kernel_version": "uname -r",
    "dm_type" : "cat /etc/X11/default-display-manager |awk -F/ '{print $NF}'"
    # "driver_version" : "dpkg -s musa musa_all-in-one |grep Version|awk -F: '{print $2}'",
    # "umd_version" : "export DISPLAY=:0.0 && glxinfo -B |grep -i 'OpenGL version string'|awk '{print $NF}'|awk -F '@' '{print $1}'" ,
    # "kmd_version" : "sudo grep 'Driver Version' /sys/kernel/debug/musa/version|awk -F[ '{print $NF}'|awk -F] '{print $1}'",
    # "glvnd" : ""
    }
    for key,command in commands.items():
        result[key] = Pc.execute(command)
    result['glvnd'] = 'glvnd'
    if result['arch'] == 'aarch64':
        result['arch'] = 'arm64'
    return result



def ping_host(hostname, count=3, timeout=3, interval=5):
    """
    Ping 主机若干次，间隔一段时间
    :param hostname: 主机名或IP地址
    :param count: Ping 次数
    :param timeout: 每次Ping的超时时间
    :param interval: 每次Ping之间的间隔
    :return: 是否可以Ping通
    """
    for _ in range(count):
        result = subprocess.run(['ping', '-c', '1', '-W', str(timeout), hostname], \
             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode == 0:
            return True
        time.sleep(interval)
    return False

def wget_url(ssh_client,url,destination_folder,file_name=None):
    # ssh_client = sshClient("192.168.114.8","swqa","gfx123456")
    log = logManager('ssh')
    if not file_name :
        file_name = url.split('/')[-1]
    destination = f"{destination_folder}/{file_name}"
    ssh_client.execute(f"mkdir -p {destination_folder}")
    rs = ssh_client.execute(f"wget --no-check-certificate  {url} -O {destination} && echo 'True' ||echo 'False'")
    if rs == 'False' :
        print(f"download {url} failed !!!")
        log.logger.error(f"package {file_name} 下载失败！！！")
        return False
    else:
        log.logger.info(f"package {file_name} 下载成功。")
        return True

def install_deb(driver_version,Pc):
    # swqa_ssh_login_cmd = f"sshpass -p gfx123456 ssh swqa@{Test_Host_IP} -o StrictHostKeyChecking=no"
    log = logManager('ssh')
    rs = get_Pc_info(Pc)
    glvnd,os_type,arch = rs['glvnd'],rs['os_type'],rs['arch']
    driver_name = f"{driver_version}+dkms+{glvnd}-{os_type}_{arch}.deb"
    work_date = re.search(r"\d{4}.\d{2}.\d{2}",driver_version)
    work_date = work_date.group()
    driver_url = f"https://oss.mthreads.com/product-release/{branch}/{work_date}/{driver_name}"
    # print('=='*10 + f"Downloading {driver_url}" + '=='*10)
    # Pc = sshClient("192.168.114.8","swqa","gfx123456")
    if 1000 == Pc.login():
        # result = Pc.execute(f"cd /home/swqa/  && mkdir deb_fallback ")
        destination_folder = "/home/swqa/deb_fallback"
        rs = wget_url(Pc,driver_url,destination_folder)
        if not rs:
            return False
        rs = Pc.execute(f"sudo apt install {destination_folder}/{driver_name} -y && \
             echo 'apt install pass' || echo 'apt install fail'")
        # check  install command run status;  
        if 'apt install fail' in rs:
            log.logger.error(f'"apt install {destination_folder}/{driver_name} -y"执行报错！')
            return False
        log.logger.info(f'"apt install {destination_folder}/{driver_name} -y"执行未报错')
        Pc.execute("sudo reboot")
        Pc.logout()

    # check driver status after reboot 
    # print('=='*10 +  f"sudo dpkg -i {driver_name} && sudo reboot" + '=='*10)
    Test_Host_IP = '192.168.114.8'
    log.logger.info(f"等待远程主机 {Test_Host_IP} 重启...")
    time.sleep(150)
    if ping_host(Test_Host_IP):
        log.logger.info(f"远程主机 {Test_Host_IP} 已重新启动")
    else:
        log.logger.error(f"远程主机 {Test_Host_IP} 无法重新启动")
        return False
    try:
        deb_version = '0'
        if 1000 == Pc.login():
            result = Pc.execute(f"dpkg -s musa")
            for line in result.splitlines():
                if "Version: " in line:
                    deb_version = line.split("Version: ")[-1]
                # print(deb_version)
            Pc.logout()
            # if deb_version != '0' and f"{driver_version}+dkms+glvnd" == deb_version and ping_rs == 0:
        if deb_version == driver_version:
            log.logger.info(f"安装成功，版本号为 {deb_version}")
            return True
        elif deb_version != '0' and deb_version != driver_version:
            log.logger.error(f"安装失败，版本号为 {deb_version}")
            return False
        else:
            log.logger.error(f"包 {driver_name} 未安装成功。")
            return False
    finally:
        pass
        

def install_umd(commit,Pc):
    rs = get_Pc_info(Pc)
    glvnd,dm_type,arch = rs['glvnd'],rs['dm_type'],rs['arch']
    # print('=='*10 + f"Downloading UMD commit {commit}" + '=='*10)
    Pc = sshClient("192.168.114.8","swqa","gfx123456")
    if 1000 == Pc.login():
        destination_folder = "/home/swqa/UMD_fallback"
        Pc.execute(f"mkdir {destination_folder}/{commit}_UMD && tar -xvf  {commit}_UMD.tar.gz -C {commit}_UMD")
        if glvnd == 'glvnd':
            UMD_commit_URL = f"http://oss.mthreads.com/release-ci/gr-umd/{branch}/{commit}_{arch}-mtgpu_linux-xorg-release-hw-{glvnd}.tar.gz"
            rs = wget_url(Pc,UMD_commit_URL,destination_folder,f"{commit}_UMD.tar.gz")
            if not rs:
                return False
            Pc.execute(f"mkdir {destination_folder}/{commit}_UMD && tar -xvf  {commit}_UMD.tar.gz -C {destination_folder}/{commit}_UMD")
            Pc.execute(f"cd {destination_folder}/{commit}_UMD/${arch}-mtgpu_linux-xorg-release/ && sudo ./install.sh -g -n -u . && sudo ./install.sh -g -n -s .")
        else:
            # glvnd 文件？
            UMD_commit_URL = f"http://oss.mthreads.com/release-ci/gr-umd/{branch}/{commit}_{arch}-mtgpu_linux-xorg-release-hw.tar.gz"
            rs = wget_url(Pc,UMD_commit_URL,destination_folder,f"{commit}_UMD.tar.gz")
            if not rs:
                return False
            Pc.execute(f"mkdir {destination_folder}/{commit}_UMD && tar -xvf  {commit}_UMD.tar.gz -C {destination_folder}/{commit}_UMD")
            Pc.execute(f"cd {destination_folder}/{commit}_UMD/${arch}-mtgpu_linux-xorg-release/ && sudo ./install.sh -u . && sudo ./install.sh -s .")
        rs = Pc.execute("[ -f /etc/ld.so.conf.d/00-mtgpu.conf ] && echo yes  || echo no")
        if rs == 'no' :
            Pc.execute("echo -e '/usr/lib/$(uname -m)-linux-gnu/musa' |sudo tee /etc/ld.so.conf.d/00-mtgpu.conf")
            if Pc.execute("uname -m") == "aarch64":
                Pc.execute("echo -e '/usr/lib/arm-linux-gnueabihf/musa' |sudo tee -a /etc/ld.so.conf.d/00-mtgpu.conf")
        Pc.execute(f"sudo ldconfig && sudo systemctl restart {dm_type}")
        Pc.logout()


def install_kmd(commit,Pc):
    rs = get_Pc_info(Pc)
    arch,dm_type,kernel_version = rs['arch'],rs['dm_type'],rs['kernel_version']
    # print('=='*10 + f"Downloading UMD commit {commit}" + '=='*10)
    KMD_commit_URL = f"http://oss.mthreads.com//sw-build/gr-kmd/{branch}/{commit}_{arch}-mtgpu_linux-xorg-release-hw.tar.gz"
    if 1000 == Pc.login():
        destination_folder = "/home/swqa/KMD_fallback"
        rs = wget_url(Pc,KMD_commit_URL,destination_folder,f"{commit}_KMD.tar.gz")
        if not rs:
            return False
        Pc.execute(f"mkdir {destination_folder}/{commit}_KMD && tar -xvf {commit}_KMD.tar.gz -C {destination_folder}/{commit}_KMD)")
        rs = Pc.execute("cd {} && find {}_KMD/ -name mtgpu.ko | awk -F '/' '{print $(NF-2)}' ".format(destination_folder,commit))
        if rs != kernel_version:
            print(f"下载的{commit}_KMD.tar.gz与{kernel_version}不匹配")
            KMD_commit_URL = f"http://oss.mthreads.com//sw-build/gr-kmd/{branch}/{commit}_{arch}-mtgpu_linux-xorg-release-hw.deb"
            Pc.execute(f"rm -rf {destination_folder}/{commit}_KMD*")
            rs = wget_url(Pc,KMD_commit_URL,destination_folder,f"{commit}_KMD.deb")
            if not rs:
                return False
            
        # 安装dkms mtgpu.deb需要卸载musa ddk
        Pc.execute(f"sudo systemctl stop {dm_type} && sleep 10 && sudo rmmod mtgpu ")
        rs =  Pc.execute(f"[ -e {destination_folder}/{commit}_KMD.tar.gz ] && echo yes  || echo no ")
        if rs == 'yes' :
            print("直接替换ko")
            dkms_rs = Pc.execute("[ -e /lib/modules/`uname -r`/updates/dkms/mtgpu.ko ] && echo yes  || echo no ")
            if dkms_rs == 'yes':
                Pc.execute("sudo mv /lib/modules/`uname -r`/updates/dkms/mtgpu.ko /lib/modules/`uname -r`/updates/dkms/mtgpu.ko.bak")
            Pc.execute(f"sudo mkdir -p /lib/modules/`uname -r`/extra/ && cd {destination_folder} && sudo cp $(find {commit}_KMD/{arch}-mtgpu_linux-xorg-release/ -name mtgpu.ko) /lib/modules/`uname -r`/extra/")
        else:
            print("安装dkms deb")
            # 需要先卸载musa,安装umd、kmd
            Pc.execute("sudo dpkg -P musa && sudo rm -rf /usr/lib/$(uname -m)-linux-gnu/musa")
            rs = Pc.execute("[ ! -d /usr/lib/$(uname -m)-linux-gnu/musa ] && echo yes || echo no ")
            if rs == 'yes':
                while True:
                    umd_commit = input("请输入要安装的UMD commitID:\n\n")
                    if umd_commit != '':
                        install_umd(umd_commit,Pc)
                        break
            Pc.execute(f"sudo dpkg -i {destination_folder}/{commit}_KMD.deb ")
        rs = Pc.execute("[ ! -e /etc/modprobe.d/mtgpu.conf ] && echo yes || echo no")
        if rs == 'yes':
            Pc.execute("echo -e 'options mtgpu display=mt EnableFWContextSwitch=27'  |sudo tee /etc/modprobe.d/mtgpu.conf")
        Pc.execute("sudo depmod -a && sudo update-initramfs -u -k `uname -r` && sudo reboot")

        Test_Host_IP = '192.168.114.8'
        log.logger.info(f"等待远程主机 {Test_Host_IP} 重启...")
        time.sleep(150)
        if ping_host(Test_Host_IP):
            log.logger.info(f"远程主机 {Test_Host_IP} 已重新启动")
        else:
            log.logger.error(f"远程主机 {Test_Host_IP} 无法重新启动")
            return False
        try:
            if 1000 == Pc.login():
                kmd_version = Pc.execute("sudo grep 'Driver Version' /sys/kernel/debug/musa/version|awk -F[ '{print $NF}'|awk -F] '{print $1}'")
                Pc.logout()
            if kmd_version == commit:
                log.logger.info(f"安装成功，版本号为 {kmd_version}")
                return True
            else:
                log.logger.error(f"kmd包 {kmd_version} 安装失败。")
                return False
        finally:
            pass

    # "${oss_url}/sw-build/gr-kmd/${branch}/${commitID}/${commitID}_${arch}-mtgpu_linux-xorg-release-hw.tar.gz"
    # "${oss_url}/sw-build/gr-kmd/${branch}/${commitID}/${commitID}_${arch}-mtgpu_linux-xorg-release-hw.deb"

def install_driver(repo,driver_version,Pc):
    if repo == 'deb':
        rs = install_deb(driver_version,Pc)
    elif repo == 'gr-umd':
        rs =install_umd(driver_version,Pc)
    elif repo == 'gr-kmd':
        rs = install_kmd(driver_version,Pc)

    test_result = ''
    # 假如安装失败了，需要怎么做？中断？还是继续寻找回退
    if not rs:
        test_result = 'install_fail'
        return test_result
    else:
        # 安装驱动后需手动测试，并输入测试结果：
        test_result = testcase()
        return test_result

def testcase():
    pass
# 二分查找，需要一个有序的数据类型，
def middle_search(repo,middle_search_list,Pc):
    # left、right初始值为列表元素的序号index 最小值和最大值
    left = 0 
    right = len(middle_search_list) - 1
    count = 0
    result = []
    left_value = install_driver(repo,middle_search_list[left],Pc)
    right_value = install_driver(repo,middle_search_list[right],Pc)
    if left_value == right_value:
        print("此区间内，第一个元素和最后一个元素的结果相等，请确认区间范围")
        return None               
    while left <= right -2 :
        middle = (left + right )//2 
        count += 1 
        mid_value = install_driver(repo,middle_search_list[middle],Pc)
        if mid_value != None and mid_value == left_value:
            left = middle 
        elif mid_value != None and mid_value == right_value:
            right = middle 
    print(f"使用二分法{count}次确认\n\n定位到问题引入范围是 {middle_search_list[left]}(不发生)-{middle_search_list[right]}(发生)之间引入") 
    return middle_search_list[left:right]

# global branch 
branch = test.branch
log = logManager('ssh')
if __name__ == "__main__":
    # Test_Host_IP = "192.168.114.26"
    # branch = 'develop'
    # arch = 'x86_64'
    # glvnd = '-glvnd'
    # driver_info_dic = get_deb_version(branch,'20240325', '20240327') 
    # driver_url_list = list(driver_info_dic.values())
    # #  driver_url_list 是列表嵌入列表的格式
    # driver_repo_tag = []
    # driver_url_ls = []
    # driver_dic = {}
    # for i in driver_url_list:
    #     driver_dic[i[-1]] = i[2]
    #     driver_repo_tag.append(i[1])

    # driver_list = list(driver_dic.keys())
    # download_url = list(driver_dic.values())
    # right = middle_search('deb',driver_list)
    # if right == -1:
    #     print('此deb区间无法确定到问题引入范围，请往更前找')
    #     sys.exit(-1)
    # repo_tag_list = [driver_repo_tag[right - 1],driver_repo_tag[right]]
    # gr_umd_list = []
    # gr_kmd_list = []
    # for repo_tag in repo_tag_list:
    #     rs = subprocess.Popen(f"curl {repo_tag}", shell=True, close_fds=True, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE).communicate()
    #     repo_tag = eval(rs[0].decode())
    #     gr_umd_list.append(repo_tag['gr-umd'][branch])
    #     gr_kmd_list.append(repo_tag['gr-kmd'][branch])
    # umd_list = get_commit.get_git_commit_info("gr-umd", "develop", "2024-02-29 00:00:00", "2024-03-01 00:00:00")
    # kmd_list = get_commit.get_git_commit_info("gr-kmd", "develop", "2024-02-29 00:00:00", "2024-03-01 00:00:00")
    # a,b = 0,0
    # for i in umd_list:
    #     if i == gr_umd_list[0]:
    #         a = umd_list.index(i)
    #     if i == gr_umd_list[-1]:
    #         b = umd_list.index(i)
    # umd_list = umd_list[a:b+1]
    # for i in kmd_list:
    #     if i == gr_kmd_list[0]:
    #         a = kmd_list.index(i)
    #     if i == gr_kmd_list[-1]:
    #         b = kmd_list.index(i)
    # kmd_list = kmd_list[a:b+1]
    # # kmd_url = []
    # # for i in umd_list: 
    # #     umd_url.append(f"http://oss.mthreads.com/release-ci/gr-umd/{branch}/{i}_{arch}-mtgpu_linux-xorg-release-hw{glvnd}.tar.gz")
    # # for i in umd_list: 
    # #     umd_url.append(f"http://oss.mthreads.com/release-ci/gr-umd/{branch}/{i}_{arch}-mtgpu_linux-xorg-release-hw{glvnd}.tar.gz")
    # # 最后拿到一个umd_comp列表，一个umd_url列表；
    # umd_right = middle_search('gr-umd',umd_list)
    # if umd_right == -1:
    #     print('umd此区间不存在问题引入，相同kmd驱动，仅更换umd驱动，结果相同。后续将测试kmd引入')
    #     kmd_right = middle_search('gr-kmd',kmd_list)
    #     if kmd_right == -1 :
    #         print('此deb区间确实有问题引入，但更换kmd、umd无法确认引入；')
    #         sys.exit(-1)
    #     else:
    #         print(f'问题引入为{kmd_list[right]}')
    # else:
    #     print(f'问题引入为{umd_list[right]}')




    driver_full_list = get_deb_version(branch,'20240325', '20240327') 
    driver_list = []
    # driver_tag_list = []
    for driver in driver_full_list:
        driver_version = driver[0]
        driver_tag = driver[1]
        driver_list.append({driver_version:None})
    print(driver_list)
    # [{'musa_2024.03.25-D+10109': None}, {'musa_2024.03.26-D+10129': None}, {'musa_2024.03.27-D+10151': None}]
    deb_rs_list = middle_search('deb',driver_list)
    if deb_rs_list == None:
        print("此deb区间无法确定到问题引入范围")
        sys.exit(-1)

    gr_umd_start_end = []
    gr_kmd_start_end = []
    for deb in deb_rs_list:
        index_of_deb = driver_full_list.index(deb)
        repo_tag_url = driver_full_list[index_of_deb][1]
        rs = subprocess.Popen(f"curl {repo_tag_url}", shell=True, close_fds=True, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE).communicate()
        repo_tag_dict = eval(rs[0].decode())
        # {'mthreads-gmi': {'develop': '775306fcc', 'master': 'b55a66c9d'}, 'mt-media-driver': {'develop': '2a48bb594'}, 'mt-pes': {'master': 'ff3b990ba'}, 'gr-kmd': {'develop': 'cfb671a2d',\
        #  'release-2.5.0-OEM': '6e65e6285'}, 'graphics-compiler': {'master': '6bfb47527'}, 'm3d': {'master': 'fad16f82a'}, 'vbios': {'master': '79c044773'}, 'ogl': {'master': '757a3724b'}, \
        # 'd3dtests': {'master': 'a88614bcc'}, 'gr-umd': {'develop': 'da0c850b8', 'release-2.5.0-OEM': '3d2e327ca'}, 'wddm': {'develop': '11ba5447c'}}
        gr_umd_start_end.append(repo_tag_dict['gr-umd'][branch])
        gr_kmd_start_end.append(repo_tag_dict['gr-kmd'][branch])
    print(gr_umd_start_end,gr_kmd_start_end)
    umd_list = get_commit.get_git_commit_info("gr-umd", "develop", "2024-02-29 00:00:00", "2024-03-01 00:00:00")
    kmd_list = get_commit.get_git_commit_info("gr-kmd", "develop", "2024-02-29 00:00:00", "2024-03-01 00:00:00")
    index_start, index_end= 0,0
    umd_rs_list = []
    kmd_rs_list = []
    for umd in umd_list:
        if umd_list.index(umd) >= umd_list.index(gr_umd_start_end[0]) and umd_list.index(umd) <= umd_list.index(gr_umd_start_end[1]):
            umd_rs_list.append({umd:None})
    for kmd in kmd_list:
        if kmd_list.index(kmd) >= kmd_list.index(gr_kmd_start_end[0]) and kmd_list.index(kmd) <= kmd_list.index(gr_kmd_start_end[1]):
            kmd_rs_list.append({umd:None})
    # for i in umd_list:
    #     if i == gr_umd_start_end[0]:
    #         index_start = umd_list.index(i)
    #     if i == gr_umd_list[-1]:
    #         index_end = umd_list.index(i)
    # umd_list = umd_list[index_start:index_end+1]
    # for i in kmd_list:
    #     if i == gr_kmd_list[0]:
    #         index_start = kmd_list.index(i)
    #     if i == gr_kmd_list[-1]:
    #         index_end = kmd_list.index(i)
    # kmd_list = kmd_list[index_start:index_end+1]

