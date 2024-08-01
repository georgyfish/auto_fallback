#!/usr/bin/python3

import os,time,sys,subprocess,re, json
import sshClient
from datetime import datetime, timezone, timedelta
from logManager import logManager
import argparse
from get_deb import deb_info
from tabulate import tabulate

log = logManager('common')

class Driver_Installer:
    def __init__(self,sshClient_obj,Pc_info,branch) -> None:
        self.log = logManager('Driver Installer')
        self.branch = branch
        self.Pc = sshClient_obj
        self.glvnd,self.arch,self.os_type,self.architecture,self.exec_user,self.kernel_version,self.dm_type=(
        Pc_info.glvnd,
        Pc_info.arch,
        Pc_info.os_type,
        Pc_info.architecture,
        Pc_info.exec_user,
        Pc_info.kernel_version,
        Pc_info.dm_type
    )

    def install_umd(self,commit):
        Pc = self.Pc
        branch,glvnd,arch,dm_type,exec_user = (
            self.branch,
            self.glvnd,
            self.arch,
            self.dm_type,
            self.exec_user
        )
        self.log.logger.info('=='*10 + f"Installing UMD commit {commit}" + '=='*10)
        destination_folder = f"/home/{exec_user}/UMD_fallback"
        # 下载
        if glvnd == 'glvnd':
            UMD_commit_URL = f"http://oss.mthreads.com/release-ci/gr-umd/{branch}/{commit}_{arch}-mtgpu_linux-xorg-release-hw-{glvnd}.tar.gz"
        else:
            UMD_commit_URL = f"http://oss.mthreads.com/release-ci/gr-umd/{branch}/{commit}_{arch}-mtgpu_linux-xorg-release-hw.tar.gz"
        
        rs = wget_url(Pc,UMD_commit_URL,destination_folder,f"{commit}_UMD.tar.gz")
        Pc.execute(f"cd {destination_folder} && mkdir -p {destination_folder}/{commit}_UMD && tar -xvf  {commit}_UMD.tar.gz -C {destination_folder}/{commit}_UMD")
        
        # 安装
        if glvnd == 'glvnd':
            Pc.execute(f"cd {destination_folder}/{commit}_UMD/{arch}-mtgpu_linux-xorg-release/ && sudo ./install.sh -g -n -u . ; sudo ./install.sh -g -n -s .")
        else:
            Pc.execute(f"cd {destination_folder}/{commit}_UMD/${arch}-mtgpu_linux-xorg-release/ && sudo ./install.sh -u . ; sudo ./install.sh -s .")
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
            log.logger.info(f"安装UMD 成功，版本号为 {Umd_Version}")
            log.logger.info('=='*10 + f"Install UMD commit {commit} Complete" + '=='*10)
            return True
        else:
            log.logger.error(f"安装UMD {commit}失败, {Umd_Version=}")
            return False

    def install_kmd(self,commit):
        Pc = self.Pc
        branch,arch,dm_type,kernel_version, exec_user = (
            self.branch,
            self.arch,
            self.dm_type,
            self.kernel_version,
            self.exec_user
        )
        self.log.logger.info('=='*10 + f"Installing KMD commit {commit}" + '=='*10)
        destination_folder = f"/home/{exec_user}/KMD_fallback"    
        if (kernel_version == '5.4.0-42-generic' and  arch == 'x86_64') or (kernel_version == '5.4.18-73-generic' and  arch == 'arm64'):
            KMD_commit_URL = f"http://oss.mthreads.com/sw-build/gr-kmd/{branch}/{commit}/{commit}_{arch}-mtgpu_linux-xorg-release-hw.tar.gz"
            wget_url(Pc,KMD_commit_URL,destination_folder,f"{commit}_KMD.tar.gz")
        else:
            KMD_commit_URL = f"http://oss.mthreads.com/sw-build/gr-kmd/{branch}/{commit}/{commit}_{arch}-mtgpu_linux-xorg-release-hw.deb"
            Pc.execute(f"rm -rf {destination_folder}/{commit}_KMD*")
            wget_url(Pc,KMD_commit_URL,destination_folder,f"{commit}_KMD.deb")
        # 安装dkms mtgpu.deb需要卸载musa ddk
        Pc.execute(f"sudo systemctl stop {dm_type}")
        time.sleep(10)
        Pc.execute("sudo rmmod mtgpu")
        rs =  Pc.execute(f"[ -e {destination_folder}/{commit}_KMD.tar.gz ] && echo yes  || echo no ")
        if rs[0] == 'yes' :
            self.log.logger.info("直接替换ko")
            Pc.execute(f"cd {destination_folder} && mkdir -p {destination_folder}/{commit}_KMD && tar -xvf {commit}_KMD.tar.gz -C {destination_folder}/{commit}_KMD")
            Pc.execute("[ -e /lib/modules/`uname -r`/updates/dkms/mtgpu.ko ] && \
                                sudo mv /lib/modules/`uname -r`/updates/dkms/mtgpu.ko /lib/modules/`uname -r`/updates/dkms/mtgpu.ko.bak")
            Pc.execute("[ ! -d /lib/modules/`uname -r`/extra/ ] && sudo mkdir -p /lib/modules/`uname -r`/extra/ ")
            Pc.execute(f"cd {destination_folder} && \
                        sudo cp $(find {commit}_KMD/{arch}-mtgpu_linux-xorg-release/ -name mtgpu.ko) /lib/modules/`uname -r`/extra/")
        else:
            self.log.logger.info(f"Install {commit} dkms deb")
            Pc.execute('sudo dkms remove mtgpu -v 1.0.0 --all')
            Pc.execute('sudo rm -rf /usr/src/mtgpu-1.0.0')
            Pc.execute(f'sudo dpkg -X {destination_folder}/{commit}_KMD.deb /')
            Pc.execute('sudo dkms add mtgpu -v 1.0.0')
            Pc.execute('sudo dkms install mtgpu -v 1.0.0')
        rs = Pc.execute("[ ! -e /etc/modprobe.d/mtgpu.conf ] && echo yes || echo no")
        if rs[0] == 'yes':
            Pc.execute("echo -e 'options mtgpu display=mt EnableFWContextSwitch=27'  |sudo tee /etc/modprobe.d/mtgpu.conf")
        Pc.execute("sudo depmod -a && sudo update-initramfs -u")
        # reboot && check kmd version 
        if Pc.reboot_and_reconnect(wait_time=30, retries=20):
            rs = Pc.execute("lsmod |grep mtgpu")[0]
            if rs:
                Kmd_Version = Pc.execute("modinfo mtgpu |grep build_version |awk '{print $NF}'")[0]
                if Kmd_Version in  commit:
                    self.log.logger.info(f"安装KMD成功，版本号为 {Kmd_Version}")
                    self.log.logger.info('=='*10 + f"Install KMD commit {commit} Complete" + '=='*10)
                    return True
                else:
                    self.log.logger.error(f"安装KMD {commit}失败, {Kmd_Version=}")
                    return False
            else:
                self.log.logger.error(f"kmd no load present !!!")
                return False
    
    def install_deb(self,driver,pc=None):
        Pc = self.Pc
        branch,glvnd,os_type,architecture, exec_user = (
            self.branch,
            self.glvnd,
            self.os_type,
            self.architecture,
            self.exec_user
        )
        self.log.logger.info('=='*10 + f"Installing  driver {driver}" + '=='*10)
        work_date = re.search(r"\d{4}.\d{2}.\d{2}",driver)
        work_date = work_date.group()
        work_date = datetime.strptime(work_date, "%Y.%m.%d")
        driver_name = f"{driver}+dkms+{glvnd}-{os_type}_{architecture}.deb"
        if pc == 'pc':
            driver_name = f"{driver}+dkms+{glvnd}-{pc}_{architecture}.deb"
        # else:
        #     # driver_name = f"{commit}+dkms+{glvnd}-{os_type}_{architecture}.deb"
        #     driver_name = f"{driver}+dkms+{glvnd}-{os_type}_{architecture}.deb"
        # if work_date > datetime.strptime("20240708","%Y%m%d"):
        #     driver_name = f"{driver}+dkms+{glvnd}-pc_{architecture}.deb"
        print(f"{driver_name=}")
        work_date = datetime.strftime(work_date, "%Y%m%d")
        driver_url = f"https://oss.mthreads.com/product-release/{branch}/{work_date}/{driver_name}"
        destination_folder = f"/home/{exec_user}/deb_fallback"
        rs = wget_url(Pc,driver_url,destination_folder)
        rs = Pc.execute(f"sudo dpkg -P musa && sudo DEBIAN_FRONTEND=noninteractive DEBCONF_NONINTERACTIVE_SEEN=true apt install {destination_folder}/{driver_name} -y --allow-downgrades && \
                echo 'apt install pass' || echo 'apt install fail'")
        # check  install command run status;  
        if 'apt install fail' in rs:
            self.log.logger.error(f'"apt install {destination_folder}/{driver_name} -y"执行报错！')
            return False
        self.log.logger.info(f'"apt install {destination_folder}/{driver_name} -y"执行未报错')
        # 重启
        if Pc.reboot_and_reconnect(wait_time=30, retries=10):
            deb_version = '0'
            result = Pc.execute(f"dpkg -s musa")
            for line in result[0].splitlines():
                if "Version: " in line:
                    deb_version = line.split("Version: ")[-1]
            driver_version = driver.split("musa_")[-1]
            if driver_version in deb_version:
                self.log.logger.info(f"driver安装成功，版本号为 {deb_version}")
                self.log.logger.info('=='*10 + f"Install  driver {driver} Complete" + '=='*10)
                return True
            elif deb_version != '0' and driver not in deb_version:
                self.log.logger.error(f"安装{driver}失败，版本号为 {deb_version}")
                return False
            else:
                self.log.logger.error(f"包 {driver_name} 未安装成功。")
                return False

    def show_kmd(self):
        Pc = self.Pc
        rs = Pc.execute("lsmod |grep mtgpu")[0]
        if rs:
            Kmd_Version = Pc.execute("modinfo mtgpu |grep build_version |awk '{print $NF}'")[0]
            if Kmd_Version:
                self.log.logger.info(f"{Kmd_Version=}")

    def show_umd(self):
        Pc = self.Pc
        display_var = Pc.execute("who | grep -o '(:[0-9]\+)' | sed 's/[()]//g' |head -n 1")[0]
        if not display_var:
            display_var = Pc.execute("w -h  | awk '{print $3}'|grep -o '^:[0-9]\+' |head -n 1")[0]
            if not display_var:
                display_var=':0'
                rs = Pc.execute(f"export DISPLAY={display_var} ; xrandr 2>$1")[0]
                if "Can't open display" in rs:
                    display_var=':1'
                    rs = Pc.execute(f"export DISPLAY={display_var} ; xrandr 2>$1")[0]
                    if "Can't open display" in rs:
                        print("xrandr failed to run with both :0 and :1")
        Umd_Version = Pc.execute(f"export DISPLAY={display_var} && glxinfo -B |grep -i 'OpenGL version string'|grep -oP '\\b[0-9a-f]{{9}}\\b(?=@)'")[0]
        if  Umd_Version :
            self.log.logger.info(f"{Umd_Version=}")
        return Umd_Version

    def get_display_var(self):
        Pc = self.Pc
        display_var = Pc.execute("who | grep -o '(:[0-9]\+)' | sed 's/[()]//g' |head -n 1")[0]
        if not display_var:
            display_var = Pc.execute("w -h  | awk '{print $3}'|grep -o '^:[0-9]\+' |head -n 1")[0]
            if not display_var:
                display_var=':0'
                rs = Pc.execute(f"export DISPLAY={display_var} ; xrandr 2>$1")[0]
                if "Can't open display" in rs:
                    display_var=':1'
                    rs = Pc.execute(f"export DISPLAY={display_var} ; xrandr 2>$1")[0]
                    if "Can't open display" in rs:
                        print("xrandr failed to run with both :0 and :1")
                        sys.exit(-1)
        return display_var

    def show_deb(self):
        Pc = self.Pc
        result = Pc.execute(f"dpkg -s musa")
        for line in result[0].splitlines():
            if "Version: " in line:
                deb_version = line.split("Version: ")[-1]
        if  deb_version:
            self.log.logger.info(f"{deb_version=}")
        return deb_version

class Config:
    # file_path = "config.json"
    def __init__(self,file_path="config.json") :
        self.file_path=file_path
        self._config_data = self.read_config()
        self.begin_date,self.end_date = self.get_default_dates()
        self.component = self._config_data.get('component','deb')
        self.commit_list = self._config_data.get('commit_list',None)
        self.branch = self._config_data.get('branch','develop')
        self.Test_Host_IP,self.Host_name,self.passwd,self.branch = (
            self._config_data['Test_Host_IP'],
            self._config_data['Host_name'],
            self._config_data['passwd'],
            self._config_data['branch']
            )
        self._parse_args()

    def read_config(self):
        with open(self.file_path, 'r') as f:
            config = json.load(f)
        return config
    
    def get_default_dates(self):
        today = datetime.today().strftime('%Y%m%d')
        one_year_ago = (datetime.today() - timedelta(days=365)).strftime('%Y%m%d')
        return self._config_data.get('begin_date',one_year_ago),self._config_data.get('end_date',today)
    
    def _parse_args(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('-b','--branch',type=str, help="branch support develop ...")
        parser.add_argument('-c','--component',type=str, choices = ['umd','kmd'], help="The component in ['umd','kmd']")
        parser.add_argument('-i','--commit_list',nargs=2, type=validate_commit, help="需输入两笔commit:'commit_pass' 'commit_fail'")
        parser.add_argument('--begin_date', type=str, help='The begin date in YYYYMMDD format')
        parser.add_argument('--end_date', type=str, help='The ending date in YYYYMMDD format')
        args = parser.parse_args()

        if args.begin_date:
            # 如果命令行参数中提供了 begin_date，则更新 begin_date 属性
            self.begin_date = args.begin_date
        if args.end_date:
            self.end_date = args.end_date
        if args.component:
            self.component = args.component
            if not args.commit_list:
                parser.error("'-c'/'--component' option requires '-i'/'--commit_list'")
            else:
                self.commit_list = args.commit_list
        if args.branch:
            self.branch = args.branch

class Pc_Info:
    def __init__(self,Pc):
        rs = self.get_Pc_info(Pc)
        self.glvnd,self.os_type,self.arch,self.architecture,self.dm_type,self.kernel_version, self.exec_user= (
        rs['glvnd'],
        rs['os_type'],
        rs['arch'],
        rs['architecture'],
        rs['dm_type'],
        rs['kernel_version'],
        rs['exec_user']
    )
    def get_Pc_info(self,Pc):
        result = {}
        commands = {
        "os_type": "cat /etc/lsb-release | head -n 1 | awk -F '='  '{print $2}'",
        "architecture": "dpkg --print-architecture",
        "arch":"uname -m" ,
        "kernel_version": "uname -r",
        "dm_type" : r"systemctl status display-manager.service|grep 'Main PID'  |grep -oP '\(\K[^)]+'",
        "exec_user" : "ps -ef |grep '/lib/systemd/systemd --user'|grep -v grep|awk -F' ' '{print $1}'|grep -vE 'lightdm|gdm'"
        }
        for key,command in commands.items():
            result[key] = Pc.execute(command)[0]
        result['glvnd'] = 'glvnd'
        if result['arch'] == 'aarch64':
            result['arch'] = 'arm64'
        return result

def validate_commit(commit):
    commit_pattern = re.compile(r'^[a-z0-9]{9}$')
    if not commit_pattern.match(commit):
        raise argparse.ArgumentTypeError(f"Invalid commit format: '{commit}'. 每个commit需满足9位包含小写字母数字的字符串")
    return commit

def wget_url(client,url,destination_folder,file_name=None):
    if not file_name :
        file_name = url.split('/')[-1]
    destination = f"{destination_folder}/{file_name}"
    client.execute(f"[ ! -d {destination_folder} ] && mkdir -p {destination_folder}")
    rs = client.execute(f"wget --no-check-certificate  {url} -O {destination} && echo 'True' ||echo 'False'")[0]
    if rs == 'False' :
        log.logger.error(f"Download {url} failed !!!")
        # log.logger.error(f"package {file_name} 下载失败！！！")
        return False
    else:
        log.logger.info(f"Download {url} success !!!")
        return True

def func(repo,data):
    headers = [repo, "Version/Commit", "result"]
    table = tabulate(data, headers=headers, tablefmt="grid")
    print(table)
    return table

def install_driver(repo,driver,Pc,Pc_info,branch,pc=None):
    driver_instller = Driver_Installer(Pc,Pc_info,branch)
    if repo == 'deb':
        rs = driver_instller.install_deb(driver,pc)
    elif repo == 'umd':
        rs = driver_instller.install_umd(driver)
    elif repo == 'kmd':
        rs = driver_instller.install_kmd(driver)
    if not rs: 
        print(f"{repo} install fail.")
        sys.exit(-1)
    # 安装完成，打印查找进度
    # func(repo,data)
    return testcase()

def testcase():
    rs = input("请手动测试后输入测试结果：pass/fail\n")
    return rs

# 二分查找
def middle_search(repo,middle_search_list,Pc,Pc_info,branch,pc_list=None):
    data  = []
    for driver in middle_search_list:
        data.append([driver,''])
    # left、right初始值为列表元素的序号index 最小值和最大值
    left = 0 
    right = len(middle_search_list) - 1
    count = 1
    # right_value = "fail"
    if repo == 'deb':
        right_value =  "fail"
        if pc_list:
            left_value = install_driver(repo,middle_search_list[left],Pc,Pc_info,branch,pc_list[left])
        else:
            left_value = install_driver(repo,middle_search_list[left],Pc,Pc_info,branch)
    else:
        left_value = install_driver(repo,middle_search_list[left],Pc,Pc_info,branch)
        right_value = install_driver(repo,middle_search_list[right],Pc,Pc_info,branch)
    if left_value == right_value:
        log.logger.info(f"{middle_search_list}区间内第一个元素和最后一个的结果相同，请确认区间范围")
        return None               
    while left <= right -2 :
        middle = (left + right )//2 
        count += 1 
        # 查找进度打印
        print(f"继续安装{middle_search_list[middle]}")
        if repo == 'deb' and pc_list:
            mid_value = install_driver(repo,middle_search_list[middle],Pc,Pc_info,branch,pc_list[middle])
        else:
            mid_value = install_driver(repo,middle_search_list[middle],Pc,Pc_info,branch)
        if mid_value != None and mid_value == left_value:
            left = middle 
        elif mid_value != None and mid_value == right_value:
            right = middle 
    log.logger.info(f"总共{count}次查找\n\n定位到问题引入范围是：\"{middle_search_list[left]}\"(不发生)-\"{middle_search_list[right]}\"(发生)之间引入") 
    return middle_search_list[left:right+1]

def run():
    config = Config()
    Test_Host_IP,Host_name,passwd,branch,begin_date,end_date,component,commit_list = (
    config.Test_Host_IP,
    config.Host_name,
    config.passwd,
    config.branch,
    config.begin_date,
    config.end_date,
    config.component,
    config.commit_list
    )
    sshClient_obj = sshClient.sshClient(Test_Host_IP,Host_name,passwd)
    Pc_info = Pc_Info(sshClient_obj)
    # print(f"{branch=}")
    # print(f"{Pc_info.os_type=}")
    deb_info_obj = deb_info(branch,begin_date, end_date,Pc_info)
    # print(deb_info_obj.get_deb_version_from_date() )
    if component and commit_list:
        commit_list = deb_info_obj.get_commits_from_commit(component,commit_list)
        rs = middle_search(component,commit_list,sshClient_obj,Pc_info,branch)
        if not rs:
            log.logger.error(f"{component} {commit_list}无法确定问题引入范围.")
    else:
        # 获取deb 列表 
        driver_list,pc_list = deb_info_obj.get_deb_version_from_date() 
        log.logger.info(f"{driver_list=}")
        log.logger.info(f"{pc_list}")
        deb_rs_list = middle_search('deb',driver_list,sshClient_obj,Pc_info,branch,pc_list)
        log.logger.info(f"deb回退结果为：\"{deb_rs_list[-1]}\"引入")
        umd_search_list, kmd_search_list = deb_info_obj.get_UMD_KMD_commit_from_deb(deb_rs_list)
        log.logger.info(f"{umd_search_list=}\n{kmd_search_list=}")
        umd_result = middle_search('umd',umd_search_list,sshClient_obj,Pc_info,branch)
        if not umd_result: 
            kmd_result = middle_search('kmd',kmd_search_list,sshClient_obj,Pc_info,branch)
        else:
            log.logger.info(f"umd 回退结果为：commitID \"{kmd_result[-1]}\"引入")


if __name__ == "__main__":
    branch = 'develop'
    begin_date = '20240711'
    end_date = '20240712'
    Test_Host_IP = '192.168.114.55'
    Host_name = 'swqa'
    passwd = 'gfx123456'
    # Test_Host_IP = '192.168.2.131'
    # Host_name = 'georgy'
    # passwd = '123456'
    sshClient_obj = sshClient.sshClient(Test_Host_IP,Host_name,passwd)
    Pc_info = Pc_Info(sshClient_obj)
    print(f"{Config().commit_list}")
    deb_info_obj = deb_info(branch,begin_date, end_date,Pc_info)
        # commit = 'b6ba94c99'
        # install_umd(commit,Pc,glvnd,os_type,arch,architecture,dm_type,kernel_version, exec_user)
        # commit = 'd8cb481ab'
        # install_kmd('d8cb481ab',Pc,glvnd,os_type,arch,architecture,dm_type,kernel_version, exec_user)
    deb_list = ['musa_2024.07.11-D+375','musa_2024.07.12-D+378']
    # umd_search_list, kmd_search_list = deb_info_obj.get_UMD_KMD_commit_from_deb(deb_list)
    # print(f"{umd_search_list=}\n{kmd_search_list=}")
    # commit = 'b6ba94c99'
    # # glvnd,arch,dm_type,exec_user,kernel_version = Pc_info.glvnd,Pc_info.arch,Pc_info.dm_type,Pc_info.exec_user,Pc_info.kernel_version
    # # install_umd(commit,Pc,branch,glvnd,arch,dm_type,exec_user)
    # commit = 'd8cb481ab'
    # # install_kmd(commit,Pc,branch,arch,dm_type,kernel_version, exec_user)
    # # Driver_Installer(Pc,Pc_info,branch).install_deb('musa_2024.07.12-D+378')
    # # s = Driver_Installer(Pc,Pc_info,branch).get_display_var()
    # # print(s)
    # umd_search_list=['7c8ea64e7', 'c68ec3906', '8db1b23d7', 'f10b58fe3', '2c07d853c', '6620adaa2', 'b6ba94c99']
    # # ['7c8ea64e7', 'c68ec3906', '8db1b23d7', 'f10b58fe3', '2c07d853c', '6620adaa2', 'b6ba94c99']
    # kmd_search_list=['c8c2488d3', 'd8b640314', 'e60ecbddd', 'd8cb481ab', 'b7e13d6eb', '9f34703f6', '2b9f60a46', 'e8110b2a3', 'a5a0caf42', 'e81d96b5d']
    # commit_list = ['7c8ea64e7', 'b6ba94c99']
    # component = 'umd'
    # # commit_list = deb_info_obj.get_commits_from_commit(component,commit_list)
    # # rs = middle_search(component,commit_list,sshClient_obj,Pc_info,branch)
    # # if not rs:
    # #     print(f"{component} {commit_list}无法确定问题引入范围.")

    deb_info_obj.get_commit_from_deb_info('musa_2024.07.11-D+375')
