#!/usr/bin/python3
from datetime import datetime, timezone, timedelta
from get_deb_version import get_deb_version
import subprocess,os,sys,get_commit,time,re
import sshClient
from logManager import logManager


# """
# 确定发生一个回退问题----》大致版本区间---》根据
# 1. 根据时间区间拿到deb大致区间   给定一个时间区间参数，分支参数；
#     test.py develop 20240501(不发生) 2023040520(发生)
#     根据时间参数--找到中间的工作日期  
#     根据工作日期对应的daily_deb   
#         curl --insecure https://oss.mthreads.com/product-release/develop/20240527/daily_build.txt
#         f"curl --insecure https://oss.mthreads.com/product-release/{branch}/{daily_tag}/daily_build.txt"
#         result = get_deb_version.get_deb_version(branch,begin_date,end_date)
#         [['musa_2024.03.26-D+10129', 'https://oss.mthreads.com/release-ci/repo_tags/20240326.txt'],
#           ['musa_2024.03.27-D+10151', 'https://oss.mthreads.com/release-ci/repo_tags/20240327.txt']]

# 2. 二分法定位:  执行deb -----> 拿到测试结果------->写入字典--->判断   ------> 继续执行deb安装-----> 拿到测试结果------->写入字典------>
# 判断   结束  -- 得到deb引入区间
#     二分查找法，根据嵌套列表的index次序 
#         每次去安装查找的那个包 得到结果 写入result 列表
#         middle_search 返回一个列表[left.right], left为不发生的index , right为发生的index
#     远程控制， 安装驱动deb 
#     install_deb()

# 3. 根据deb 区间  定位到UMD、KMD commit区间 
#     result[left][1] = 'https://oss.mthreads.com/release-ci/repo_tags/20240326.txt'
#     result[left][2] = 'https://oss.mthreads.com/release-ci/repo_tags/20240327.txt'
#     curl 'https://oss.mthreads.com/release-ci/repo_tags/20240326.txt'  ---》 {"mthreads-gmi":{"develop":"15d1e9380","master":"8ee556f92"},"mt-pes":{"master":"7202a31dc"},"mt-management":\
#         {"develop":"dad852321","master":"6c374091d"},"mt-media-driver":{"develop":"7e4ecb1cc"},"DirectStream":{"develop":"208e5240d"},"gr-kmd":{"develop":"69d7e3104",\
#             "release-2.5.0-OEM":"8c51763a1"},"graphics-compiler":{"master":"545ffa3a9"},"m3d":{"master":"a9567d601"},"mtdxum":{"master":"9cac086dd"},"d3dtests":{"master":"bd0358ed2"},\
#                 "ogl":{"master":"44be1b68a"},"gr-umd":{"develop":"6dd19a265","release-2.5.0-OEM":"27a85ebf5"},"wddm":{"develop":"d23c6060d"}}
#     字典嵌套字典  
#         dict['gr-umd']["develop"]  ---> UMD commitID


# 4. 定位UMD commit引入
#     获取UMD commitID 列表
#     方法一：
#         爬取commit网页，修改begin时间和end时间，筛选出一个umd_commit list，再根据第3步获取的区间，截取、切片找到需要的umd_commit_list；
#     方法二：
#         使用get_lib.get_git_commit_info() 获取所有的git commit信息，再写一个根据第3步获取的区间得到需要的umd_commit_list的方法；
    

# 5. UMD定位不到  执行KMD定位

# 定位umd_commit:
# 1. get_commit   commit_begin  commit_end
# 2. middle_search()----> 区间

# """


def slice_full_list(start_end_list, full_list):
    try:
        if start_end_list[0] in full_list:
            index_start = full_list.index(start_end_list[0])
        else:
            log.logger.error("input error!")
            sys.exit(-1)
        if start_end_list[1] in full_list:
            index_end = full_list.index(start_end_list[1])
        else:
            log.logger.error("input error!")
            sys.exit(-1)        
        return full_list[index_start:index_end+1]
    except IndexError:
        log.logger.error(f"list index out of range! {start_end_list} not in {full_list}")
        sys.exit(-1)


def check_umd_url(umd_search_list):
    rs = []
    for commit in umd_search_list:
        url = f"http://oss.mthreads.com/release-ci/gr-umd/{branch}/{commit}_{arch}-mtgpu_linux-xorg-release-hw.tar.gz"
        if glvnd:
            url = f"http://oss.mthreads.com/release-ci/gr-umd/{branch}/{commit}_{arch}-mtgpu_linux-xorg-release-hw-{glvnd}.tar.gz"
        try:
            result = subprocess.run(
                ['wget', '--spider', '-q', url], # --spider 表示不下载，只检查，-q 表示安静模式
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            if result.returncode == 0:
                rs.append(commit)
            else:
                log.logger.error(f"{url}地址不存在，移除UMD {commit}")
        except Exception as e:
            log.logger.error(f"An error occurred: {e}")
            # return False
    return rs

def check_kmd_url(kmd_search_list):
    rs = []
    for commit in kmd_search_list:
        url = f"http://oss.mthreads.com/sw-build/gr-kmd/{branch}/{commit}/{commit}_{arch}-mtgpu_linux-xorg-release-hw.deb"
        try:
            result = subprocess.run(
                ['wget', '--spider', '-q', url], # --spider 表示不下载，只检查，-q 表示安静模式
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            if result.returncode == 0:
                rs.append(commit)
            else:
                log.logger.error(f"{url}地址不存在，移除KMD {commit}")
        except Exception as e:
            log.logger.error(f"An error occurred: {e}")
            # return False
    return rs

def get_commit_from_deb(deb_rs_list,driver_full_list):
    gr_umd_start_end = []
    gr_kmd_start_end = []
    for deb_info in driver_full_list:
        if deb_info[0] in deb_rs_list:
            # rs = subprocess.Popen(f"curl {deb_info[1]}", shell=True, close_fds=True, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE).communicate()
            log.logger.info(f"curl {deb_info[1]}")
            try:
                rs = subprocess.run(['curl', deb_info[1]], capture_output=True, text=True, check=True)
                repo_tag_dict = eval(rs.stdout)
                log.logger.info(f"{repo_tag_dict=}")
                # result.append(stdout_list)
                gr_umd_start_end.append(repo_tag_dict['gr-umd'][branch])
                gr_kmd_start_end.append(repo_tag_dict['gr-kmd'][branch])
            except subprocess.CalledProcessError as e:
                log.logger.error(f"Error:\n{e.stderr}")
            except Exception as e:
                log.logger.error(f"An unexpected error occurred: \n{e}")
    log.logger.info(f"{gr_umd_start_end=}\n{gr_kmd_start_end=}\n")
    begin_date = re.search(r"\d{4}.\d{2}.\d{2}",deb_rs_list[0]).group()
    end_date = re.search(r"\d{4}.\d{2}.\d{2}",deb_rs_list[1]).group()
    previous_day = datetime.strptime(begin_date,"%Y.%m.%d") - timedelta(days=1)
    # 设置开始时间为前一天12:00，结束时间为当天的23:00
    commit_begin_date = previous_day.replace(hour=12, minute=0, second=0).strftime("%Y-%m-%d %H:%M:%S")
    commit_end_date = datetime.strptime(end_date,"%Y.%m.%d").replace(hour=23,minute=0,second=0).strftime("%Y-%m-%d %H:%M:%S")
    # 格式化输出
    log.logger.info(f"查询开始时间：{commit_begin_date}\n查询结束时间：{commit_end_date}\n")    
    umd_list = get_commit.get_git_commit_info("gr-umd", branch, commit_begin_date , commit_end_date)
    kmd_list = get_commit.get_git_commit_info("gr-kmd", branch, commit_begin_date , commit_end_date)
    log.logger.info(f"{umd_list=}\n{kmd_list=}\n")
    umd_search_list , kmd_search_list = slice_full_list(gr_umd_start_end,umd_list) , slice_full_list(gr_kmd_start_end,kmd_list)
    log.logger.info(f"{umd_search_list=}\n{kmd_search_list=}\n")
    umd_search_list,kmd_search_list = check_umd_url(umd_search_list),check_kmd_url(kmd_search_list)
    return umd_search_list,kmd_search_list

def deb_fallback(driver_list,Pc):
    deb_rs_list = middle_search('deb',driver_list,Pc)
    if not deb_rs_list:
        log.logger.error(f"{driver_list} deb区间无法确定问题引入范围")
        sys.exit(-1)
    return deb_rs_list

def umd_fallback(umd_search_list,Pc):
    umd_rs_list = middle_search('gr-umd',umd_search_list,Pc)
    if not umd_rs_list:
        log.logger.error(f"{umd_search_list} UMD区间无法确定问题引入范围")
        # sys.exit(-1)
    return umd_rs_list

def kmd_fallback(kmd_search_list,Pc):
    kmd_rs_list = middle_search('gr-kmd',kmd_search_list,Pc)
    if not kmd_rs_list:
        log.logger.error(f"{kmd_search_list} 此KMD区间无法确定问题引入范围")
        sys.exit(-1)
    return kmd_rs_list

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
    "dm_type" : "cat /etc/X11/default-display-manager |awk -F/ '{print $NF}'",
    # "driver_version" : "dpkg -s musa musa_all-in-one |grep Version|awk -F: '{print $2}'",
    # "umd_version" : "export DISPLAY=:0.0 && glxinfo -B |grep -i 'OpenGL version string'|awk '{print $NF}'|awk -F '@' '{print $1}'" ,
    # "kmd_version" : "sudo grep 'Driver Version' /sys/kernel/debug/musa/version|awk -F[ '{print $NF}'|awk -F] '{print $1}'",
    # "glvnd" : ""
    "exec_user" : "ps -ef |grep '/lib/systemd/systemd --user'|grep -v grep|awk -F' ' '{print $1}'|grep -vE 'lightdm|gdm'"
    }
    for key,command in commands.items():
        result[key] = Pc.execute(command)[0]
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

def wget_url(client,url,destination_folder,file_name=None):
    if not file_name :
        file_name = url.split('/')[-1]
    destination = f"{destination_folder}/{file_name}"
    client.execute(f"mkdir -p {destination_folder}")
    rs = client.execute(f"wget --no-check-certificate  {url} -O {destination} && echo 'True' ||echo 'False'")[0]
    if rs == 'False' :
        log.logger.error(f"Download {url} failed !!!")
        # log.logger.error(f"package {file_name} 下载失败！！！")
        return False
    else:
        log.logger.info(f"Download {url} success !!!")
        return True

def install_deb(driver_version,Pc):
    log.logger.info('=='*10 + f"Installing  driver {driver_version}" + '=='*10)
    driver_name = f"{driver_version}+dkms+{glvnd}-{os_type}_{architecture}.deb"
    work_date = re.search(r"\d{4}.\d{2}.\d{2}",driver_version)
    work_date = work_date.group()
    work_date = datetime.strptime(work_date, "%Y.%m.%d")
    work_date = datetime.strftime(work_date, "%Y%m%d")
    driver_url = f"https://oss.mthreads.com/product-release/{branch}/{work_date}/{driver_name}"
    # if 1000 == Pc.login():
    destination_folder = f"/home/{exec_user}/deb_fallback"
    rs = wget_url(Pc,driver_url,destination_folder)
    if not rs:
        return False
    rs = Pc.execute(f"sudo dpkg -P musa && sudo apt install {destination_folder}/{driver_name} -y --allow-downgrades && \
            echo 'apt install pass' || echo 'apt install fail'")
    # check  install command run status;  
    if 'apt install fail' in rs:
        log.logger.error(f'"apt install {destination_folder}/{driver_name} -y"执行报错！')
        return False
    log.logger.info(f'"apt install {destination_folder}/{driver_name} -y"执行未报错')
    # Pc.execute("sudo reboot")
    if Pc.reboot_and_reconnect(wait_time=30, retries=10):
        deb_version = '0'
        result = Pc.execute(f"dpkg -s musa")
        for line in result[0].splitlines():
            if "Version: " in line:
                deb_version = line.split("Version: ")[-1]
        driver_version = driver_version.split("musa_")[-1]
        if driver_version in deb_version:
            log.logger.info(f"driver安装成功，版本号为 {deb_version}")
            log.logger.info(f"driver安装成功，版本号为 {deb_version}")
            log.logger.info('=='*10 + f"Install  driver {driver_version} Complete" + '=='*10)
            return True
        elif deb_version != '0' and driver_version not in deb_version:
            log.logger.error(f"driver安装{driver_version}失败，版本号为 {deb_version}")
            log.logger.error(f"driver安装{driver_version}失败，版本号为 {deb_version}")
            return False
        else:
            log.logger.error(f"包 {driver_name} 未安装成功。")
            return False
        
def install_umd(commit,Pc):
    log.logger.info('=='*10 + f"Installing UMD commit {commit}" + '=='*10)
    destination_folder = f"/home/{exec_user}/UMD_fallback"
    # Pc.execute(f"mkdir {destination_folder}/{commit}_UMD && tar -xvf  {commit}_UMD.tar.gz -C {commit}_UMD")
    if glvnd == 'glvnd':
        UMD_commit_URL = f"http://oss.mthreads.com/release-ci/gr-umd/{branch}/{commit}_{arch}-mtgpu_linux-xorg-release-hw-{glvnd}.tar.gz"
        rs = wget_url(Pc,UMD_commit_URL,destination_folder,f"{commit}_UMD.tar.gz")
        if not rs:
            
            return False
        Pc.execute(f"cd {destination_folder} && mkdir -p {destination_folder}/{commit}_UMD && tar -xvf  {commit}_UMD.tar.gz -C {destination_folder}/{commit}_UMD")
        Pc.execute(f"cd {destination_folder}/{commit}_UMD/{arch}-mtgpu_linux-xorg-release/ && sudo ./install.sh -g -n -u . && sudo ./install.sh -g -n -s .")
    else:
        # glvnd 文件？
        UMD_commit_URL = f"http://oss.mthreads.com/release-ci/gr-umd/{branch}/{commit}_{arch}-mtgpu_linux-xorg-release-hw.tar.gz"
        rs = wget_url(Pc,UMD_commit_URL,destination_folder,f"{commit}_UMD.tar.gz")
        if not rs:
            return False
        Pc.execute(f"cd {destination_folder} && mkdir -p {destination_folder}/{commit}_UMD && tar -xvf  {commit}_UMD.tar.gz -C {destination_folder}/{commit}_UMD")
        Pc.execute(f"cd {destination_folder}/{commit}_UMD/${arch}-mtgpu_linux-xorg-release/ && sudo ./install.sh -u . && sudo ./install.sh -s .")
    rs = Pc.execute("[ -f /etc/ld.so.conf.d/00-mtgpu.conf ] && echo yes  || echo no")[0]
    if rs == 'no' :
        Pc.execute("echo -e /usr/lib/$(uname -m)-linux-gnu/musa |sudo tee /etc/ld.so.conf.d/00-mtgpu.conf")
        if Pc.execute("uname -m")[0] == "aarch64":
            Pc.execute("echo -e '/usr/lib/arm-linux-gnueabihf/musa' |sudo tee -a /etc/ld.so.conf.d/00-mtgpu.conf")
    Pc.execute(f"sudo ldconfig && sudo systemctl restart {dm_type}")
    # check umd version
    time.sleep(10)
    Umd_Version = Pc.execute("export DISPLAY=:0.0 && glxinfo -B |grep -i 'OpenGL version string'|grep -oP '\\b[0-9a-f]{9}\\b(?=@)'")[0]
    if Umd_Version == commit:
        log.logger.info(f"安装成功，版本号为 {Umd_Version}")
        log.logger.info('=='*10 + f"Install UMD commit {commit} Complete" + '=='*10)
        return True
    else:
        log.logger.error(f"安装UMD {commit}失败, {Umd_Version=}")
        return False

def install_kmd(commit,Pc):
    # Download KMD tar or dkms-deb
    log.logger.info('=='*10 + f"Installing KMD commit {commit}" + '=='*10)
    KMD_commit_URL = f"http://oss.mthreads.com/sw-build/gr-kmd/{branch}/{commit}/{commit}_{arch}-mtgpu_linux-xorg-release-hw.tar.gz"
    # https://oss.mthreads.com/sw-build/gr-kmd/develop/7a52195ed/7a52195ed_x86_64-mtgpu_linux-xorg-release-hw.tar.gz
    destination_folder = f"/home/{exec_user}/KMD_fallback"
    rs = wget_url(Pc,KMD_commit_URL,destination_folder,f"{commit}_KMD.tar.gz")
    if not rs:
        return False
    Pc.execute(f"cd {destination_folder} && mkdir -p {destination_folder}/{commit}_KMD && tar -xvf {commit}_KMD.tar.gz -C {destination_folder}/{commit}_KMD")
    rs = Pc.execute("cd %s && find %s_KMD -name mtgpu.ko | awk -F '/' '{print $(NF-2)}' " % (destination_folder,commit))
    if rs[0] != kernel_version:
        log.logger.info(f"下载的{commit}_KMD.tar.gz与{kernel_version}不匹配")
        KMD_commit_URL = f"http://oss.mthreads.com/sw-build/gr-kmd/{branch}/{commit}/{commit}_{arch}-mtgpu_linux-xorg-release-hw.deb"
        Pc.execute(f"rm -rf {destination_folder}/{commit}_KMD*")
        rs = wget_url(Pc,KMD_commit_URL,destination_folder,f"{commit}_KMD.deb")
        if not rs:
            return False
    # 安装dkms mtgpu.deb需要卸载musa ddk
    Pc.execute(f"sudo systemctl stop {dm_type}")
    time.sleep(10)
    Pc.execute("sudo rmmod mtgpu")
    rs =  Pc.execute(f"[ -e {destination_folder}/{commit}_KMD.tar.gz ] && echo yes  || echo no ")
    if rs[0] == 'yes' :
        log.logger.info("直接替换ko")
        dkms_rs = Pc.execute("[ -e /lib/modules/`uname -r`/updates/dkms/mtgpu.ko ] && echo yes  || echo no ")
        if dkms_rs[0] == 'yes':
            Pc.execute("sudo mv /lib/modules/`uname -r`/updates/dkms/mtgpu.ko /lib/modules/`uname -r`/updates/dkms/mtgpu.ko.bak")
        Pc.execute(f"sudo mkdir -p /lib/modules/`uname -r`/extra/ && cd {destination_folder} && sudo cp $(find {commit}_KMD/{arch}-mtgpu_linux-xorg-release/ -name mtgpu.ko) /lib/modules/`uname -r`/extra/")
    else:
        log.logger.info(f"Install {commit} dkms deb")
        # 需要先卸载musa,安装umd、kmd
        Pc.execute("sudo dpkg -P musa && sudo rm -rf /usr/lib/$(uname -m)-linux-gnu/musa")
        rs = Pc.execute("[ ! -d /usr/lib/$(uname -m)-linux-gnu/musa ] && echo yes || echo no ")
        if rs[0] == 'yes':
            while True:
                umd_commit = input("请输入要安装的UMD commitID:\n\n")
                if umd_commit != '':
                    install_umd(umd_commit,Pc)
                    break
        Pc.execute(f"sudo dpkg -i {destination_folder}/{commit}_KMD.deb ")
    rs = Pc.execute("[ ! -e /etc/modprobe.d/mtgpu.conf ] && echo yes || echo no")
    if rs[0] == 'yes':
        Pc.execute("echo -e 'options mtgpu display=mt EnableFWContextSwitch=27'  |sudo tee /etc/modprobe.d/mtgpu.conf")
    Pc.execute("sudo depmod -a && sudo update-initramfs -u -k `uname -r`")
    # reboot && check kmd version 
    if Pc.reboot_and_reconnect(wait_time=30, retries=20):
        rs = Pc.execute("lsmod |grep mtgpu")[0]
        if rs:
            Kmd_Version = Pc.execute("modinfo mtgpu |grep build_version |awk '{print $NF}'")[0]
            if Kmd_Version in  commit:
                log.logger.info(f"安装KMD成功，版本号为 {Kmd_Version}")
                log.logger.info('=='*10 + f"Install KMD commit {commit} Complete" + '=='*10)
                return True
            else:
                log.logger.error(f"安装KMD {commit}失败, {Kmd_Version=}")
                return False
        else:
            log.logger.error(f"kmd no load present !!!")
            return False

def install_driver(repo,driver_version,Pc):
    if repo == 'deb':
        rs = install_deb(driver_version,Pc)
    elif repo == 'gr-umd':
        rs =install_umd(driver_version,Pc)
    elif repo == 'gr-kmd':
        rs = install_kmd(driver_version,Pc)
    test_result = ''
    if not rs:
        test_result = 'fail'
        return test_result
    else:
        test_result = testcase()
        return test_result

def testcase():
    rs = input("请手动测试后输入测试结果：pass/fail\n")
    return rs

# 二分查找
def middle_search(repo,middle_search_list,Pc):
    # left、right初始值为列表元素的序号index 最小值和最大值
    left = 0 
    right = len(middle_search_list) - 1
    count = 2
    left_value = install_driver(repo,middle_search_list[left],Pc)
    right_value = install_driver(repo,middle_search_list[right],Pc)
    if left_value == right_value:
        log.logger.info(f"{middle_search_list}区间内第一个元素和最后一个的结果相同，请确认区间范围")
        return None               
    while left <= right -2 :
        middle = (left + right )//2 
        count += 1 
        mid_value = install_driver(repo,middle_search_list[middle],Pc)
        if mid_value != None and mid_value == left_value:
            left = middle 
        elif mid_value != None and mid_value == right_value:
            right = middle 
    log.logger.info(f"总共{count}次查找\n\n定位到问题引入范围是：\"{middle_search_list[left]}\"(不发生)-\"{middle_search_list[right]}\"(发生)之间引入") 
    return middle_search_list[left:right]

def main(branch,begin_date,end_date,Pc):
    driver_full_list = get_deb_version(branch,begin_date, end_date) 
    driver_list = []
    if not driver_full_list:
        log.logger.error("Get driver_full_list is empty! Please check driver date!")
        sys.exit(-1)
    elif len(driver_full_list) == 1 :
        log.logger.info(f"{len(driver_full_list)=} ; Please check driver date!")
    for driver in driver_full_list:
        driver_version = driver[0]
        driver_list.append(driver_version)
    log.logger.info(f"{driver_list=}")
    deb_rs_list = deb_fallback(driver_list,Pc)
    # deb_rs_list = ['musa_2024.07.01-D+11670', 'musa_2024.07.02-D+11693']
    umd_search_list, kmd_search_list = get_commit_from_deb(deb_rs_list,driver_full_list)
        # {'mthreads-gmi': {'develop': '775306fcc', 'master': 'b55a66c9d'}, 'mt-media-driver': {'develop': '2a48bb594'}, 'mt-pes': {'master': 'ff3b990ba'}, 'gr-kmd': {'develop': 'cfb671a2d',\
        #  'release-2.5.0-OEM': '6e65e6285'}, 'graphics-compiler': {'master': '6bfb47527'}, 'm3d': {'master': 'fad16f82a'}, 'vbios': {'master': '79c044773'}, 'ogl': {'master': '757a3724b'}, \
        # 'd3dtests': {'master': 'a88614bcc'}, 'gr-umd': {'develop': 'da0c850b8', 'release-2.5.0-OEM': '3d2e327ca'}, 'wddm': {'develop': '11ba5447c'}}
    if not umd_fallback(umd_search_list,Pc): 
        kmd_fallback(kmd_search_list,Pc)



if __name__ == "__main__":
    branch = 'develop'
    begin_date = '20240611'
    end_date = '20240702'
    Test_Host_IP = '192.168.114.55'
    Host_name = 'swqa'
    passwd = 'gfx123456'
    log = logManager('Fallback Test')
    Pc = sshClient.sshClient(Test_Host_IP,Host_name,passwd)
    if 1000 == Pc.login():
        rs = get_Pc_info(Pc)
        print(f"{rs=}")
        glvnd,os_type,arch,architecture,dm_type,kernel_version, exec_user= (
            rs['glvnd'],
            rs['os_type'],
            rs['arch'],
            rs['architecture'],
            rs['dm_type'],
            rs['kernel_version'],
            rs['exec_user']
        )
        main(branch,begin_date,end_date,Pc)
        # driver_full_list = get_deb_version(branch,begin_date, end_date) 
        # print(f"{driver_full_list=}")
        # driver_list = []
        # for driver in driver_full_list:
        #     driver_version = driver[0]
        #     driver_list.append(driver_version)
        # print(f"{driver_list=}")
        # deb_rs_list = deb_fallback(driver_list,Pc)
        # print(f"{deb_rs_list=}")
        # deb_rs_list = ['musa_2024.07.01-D+11670', 'musa_2024.07.02-D+11693']
        # umd_search_list, kmd_search_list = get_commit_from_deb(deb_rs_list,driver_full_list)
        # install_umd('4b3b7068f',Pc)
        # install_kmd('7a52195ed',Pc)
        # umd_search_list = ['5efbca234', '4b3b7068f', 'fb15a8f46', '08cd254f3', 'b47553c08', 'de9c3e598']
        # umd_search_list = check_umd_url(umd_search_list)
        # umd_search_list = check_umd_url(umd_search_list)
        # umd_fallback(umd_search_list,Pc)
