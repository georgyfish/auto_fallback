#!/usr/bin/python3

import time,sys,re,os
from datetime import datetime
from tabulate import tabulate
basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(basedir)
from lib.get_driver_info import deb_info
from lib.logManager import logManager
from lib import sshClient
from config import Config

class Fallback:
    def __init__(self,timeout=60*60):
        self.VALID_OS_TYPE = {"Kylin", "Ubuntu", "UOS"}
        self.timeout = timeout
        self.config = Config()
        self.log = logManager(self.config.ip,'Fallback')

        self.sshclient = sshClient.sshClient(self.config.ip,self.config.Host_name,self.config.passwd)

    

    @staticmethod
    def testcase():
        rs = input("请手动测试后输入测试结果：pass/fail\n")
        return rs

    def install_driver(self,repo,driver,pc=None):
        if repo == 'deb':
            rs = self.install_deb(driver,pc)
        elif repo == 'umd':
            rs = self.install_umd(driver)
        elif repo == 'kmd':
            rs = self.install_kmd(driver)
        if not rs: 
            print(f"{repo} install fail.")
            sys.exit(-1)
        return Fallback.testcase()

    @staticmethod
    def print_table(data):
        # 后续写入csv?
        headers = ["Version/Commit", "result"]
        table = tabulate(data, headers=headers, tablefmt="grid")
        # print(table)
        return table

    def middle_search(self,repo,search_list,pc_list=None):
        data  = []
        for driver in search_list:
            data.append([repo,driver,''])
        # left、right初始值为列表元素的序号index 最小值和最大值
        left = 0 
        right = len(search_list) - 1
        count = 1
        if repo == 'deb':
            data[right][-1] =  "fail"
            if pc_list:
                data[left][-1] = self.install_driver(repo,search_list[left],pc_list[left])
            else:
                data[left][-1] = self.install_driver(repo,search_list[left])
        else:
            data[left][-1] = self.install_driver(repo,search_list[left])
            data[right][-1] = self.install_driver(repo,search_list[right])
        self.log.logger.info(f"回退进度：\n{Fallback.print_table(data)}")
        if data[left][-1] == data[right][-1]:
            self.log.logger.info(f"{search_list}区间内第一个元素和最后一个的结果相同，请确认回退区间范围")
            return None               
        while left <= right -2 :
            middle = (left + right )//2 
            count += 1 
            # 查找进度打印

            if repo == 'deb' and pc_list:
                data[middle][-1] = self.install_driver(repo,search_list[middle],pc_list[middle])
            else:
                data[middle][-1] = self.install_driver(repo,search_list[middle])
            # Fallback.print_table(data)
            self.log.logger.info(f"回退进度：\n{Fallback.print_table(data)}")
            if data[middle][-1] != None and data[middle][-1] == data[left][-1]:
                left = middle 
            elif data[middle][-1] != None and data[middle][-1] == data[right][-1]:
                right = middle 
        self.log.logger.info(f"总共{count}次回退查找\n\n定位到问题引入范围是：\"{search_list[left]}\"(不发生)-\"{search_list[right]}\"(发生)之间引入") 
        return search_list[left:right+1]

    def find_regression(self):
        config = self.config
        branch,begin_date,end_date,component,commit_list = (
            config.branch,
            config.begin_date,
            config.end_date,
            config.component,
            config.commit_list
        )
        # sshClient_obj = self.sshclient
        pc_info = self.sshclient.info

        deb_info_obj = deb_info(branch,begin_date, end_date,pc_info,self.log)

        if commit_list:
            commit_list = deb_info_obj.get_commits_from_commit(component,commit_list)
            self.log.logger.info(f"{component} 回退列表为：{commit_list}")
            rs = self.middle_search(component,commit_list)
            if rs:
                self.log.logger.info(f"{component} 回退结果为：\"{rs[-1]}\"引入")
                # self.keylog.keyinfo_logger.info(f"{component} 回退结果为：\"{rs[-1]}\"引入")
        else:
            # 获取deb 列表 
            # self.keylog.keyinfo_logger.info("=="*30+"Step 1 - 获取deb列表"+"=="*30)
            driver_list,pc_list = deb_info_obj.get_deb_version_from_date() 
            self.log.logger.info(f"'deb' 回退列表为：{driver_list}")
            rs = self.middle_search(component,driver_list,pc_list)
            if rs:
                self.log.logger.info(f"deb回退结果为：\"{rs[-1]}\"引入")
                # 获取umd、kmd info，后续可添加video、gmi
                umd_list, kmd_list = deb_info_obj.get_UMD_KMD_commit_from_deb(rs)
                component = 'umd'
                self.log.logger.info(f"{component} 回退列表为：{umd_list}")
                rs = self.middle_search(component,umd_list)
                if not rs: 
                    component = 'kmd'
                    self.log.logger.info(f"{component} 回退列表为：{kmd_list}")
                    rs = self.middle_search(component,kmd_list)
                self.log.logger.info(f"{component} 回退结果为：\"{rs[-1]}\"引入")

    def install_umd(self,commit):
        Pc = self.sshclient
        branch,glvnd,arch,dm_type,exec_user = (
            self.config.branch,
            Pc.info['glvnd'],
            Pc.info['arch'],
            Pc.info['dm_type'],
            Pc.info['exec_user']
        )
        self.log.logger.info('=='*10 + f"Installing UMD commit {commit}" + '=='*10)
        fallback_folder = f"/home/{exec_user}/Fallback/UMD_Fallback"
        # 下载
        if glvnd == 'glvnd':
            UMD_commit_URL = f"http://oss.mthreads.com/release-ci/gr-umd/{branch}/{commit}_{arch}-mtgpu_linux-xorg-release-hw-{glvnd}.tar.gz"
        else:
            UMD_commit_URL = f"http://oss.mthreads.com/release-ci/gr-umd/{branch}/{commit}_{arch}-mtgpu_linux-xorg-release-hw.tar.gz"

        Pc.wget_url(UMD_commit_URL,fallback_folder,f"{commit}_UMD.tar.gz")
        Pc.execute(f"cd {fallback_folder} && mkdir -p {fallback_folder}/{commit}_UMD && tar -xvf  {commit}_UMD.tar.gz -C {fallback_folder}/{commit}_UMD")
        
        # 安装
        if glvnd == 'glvnd':
            Pc.execute(f"cd {fallback_folder}/{commit}_UMD/{arch}-mtgpu_linux-xorg-release/ && sudo ./install.sh -g -n -u . ; sudo ./install.sh -g -n -s .")
        else:
            #非glvnd umd安装，修改Xorg path
            Pc.execute(f"cd {fallback_folder}/{commit}_UMD/{arch}-mtgpu_linux-xorg-release/ && sudo ./install.sh -u . ; sudo ./install.sh -s .")
        rs = Pc.execute("[ -f /etc/ld.so.conf.d/00-mtgpu.conf ] && echo yes  || echo no")[0]
        if rs == 'no' :
            Pc.execute("echo -e /usr/lib/$(uname -m)-linux-gnu/musa |sudo tee /etc/ld.so.conf.d/00-mtgpu.conf")
            if Pc.execute("uname -m")[0] == "aarch64":
                Pc.execute("echo -e '/usr/lib/arm-linux-gnueabihf/musa' |sudo tee -a /etc/ld.so.conf.d/00-mtgpu.conf")
        Pc.execute(f"sudo ldconfig && sudo systemctl restart {dm_type}")
        # check umd version
        time.sleep(10)
        # Umd_Version = Pc.execute("export DISPLAY=:0.0 && glxinfo -B |grep -i 'OpenGL version string'|grep -oP '\\b[0-9a-f]{9}\\b(?=@)'")[0]
        Umd_Version = self.show_umd()
        if Umd_Version == commit:
            self.log.logger.info(f"安装UMD 成功，版本号为 {Umd_Version}")
            self.log.logger.info('=='*10 + f"Install UMD commit {commit} Complete" + '=='*10)
            return True
        else:
            self.log.logger.error(f"安装UMD {commit}失败, {Umd_Version=}")
            return False

    def install_kmd(self,commit):
        Pc = self.sshclient
        branch,arch,dm_type,kernel_version, exec_user = (
            self.config.branch,
            Pc.info['arch'],
            Pc.info['dm_type'],
            Pc.info['kernel_version'],
            Pc.info['exec_user']
        )
        self.log.logger.info('=='*10 + f"Installing KMD commit {commit}" + '=='*10)
        fallback_folder = f"/home/{exec_user}/Fallback/KMD_Fallback"    
        if (kernel_version == '5.4.0-42-generic' and  arch == 'x86_64') or (kernel_version == '5.4.18-73-generic' and  arch == 'arm64'):
            KMD_commit_URL = f"http://oss.mthreads.com/sw-build/gr-kmd/{branch}/{commit}/{commit}_{arch}-mtgpu_linux-xorg-release-hw.tar.gz"
            Pc.wget_url(KMD_commit_URL,fallback_folder,f"{commit}_KMD.tar.gz")
        else:
            KMD_commit_URL = f"http://oss.mthreads.com/sw-build/gr-kmd/{branch}/{commit}/{commit}_{arch}-mtgpu_linux-xorg-release-hw.deb"
            Pc.execute(f"rm -rf {fallback_folder}/{commit}_KMD*")
            Pc.wget_url(KMD_commit_URL,fallback_folder,f"{commit}_KMD.deb")
        # 安装dkms mtgpu.deb需要卸载musa ddk
        Pc.execute(f"sudo systemctl stop {dm_type}")
        time.sleep(10)
        Pc.execute("sudo rmmod mtgpu")
        rs =  Pc.execute(f"[ -e {fallback_folder}/{commit}_KMD.tar.gz ] && echo yes  || echo no ")
        if rs[0] == 'yes' :
            self.log.logger.info("直接替换ko")
            Pc.execute(f"cd {fallback_folder} && mkdir -p {fallback_folder}/{commit}_KMD && tar -xvf {commit}_KMD.tar.gz -C {destination_folder}/{commit}_KMD")
            Pc.execute("[ -e /lib/modules/`uname -r`/updates/dkms/mtgpu.ko ] && \
                                sudo mv /lib/modules/`uname -r`/updates/dkms/mtgpu.ko /lib/modules/`uname -r`/updates/dkms/mtgpu.ko.bak")
            Pc.execute("[ ! -d /lib/modules/`uname -r`/extra/ ] && sudo mkdir -p /lib/modules/`uname -r`/extra/ ")
            Pc.execute(f"cd {fallback_folder} && \
                        sudo cp $(find {commit}_KMD/{arch}-mtgpu_linux-xorg-release/ -name mtgpu.ko) /lib/modules/`uname -r`/extra/")
        else:
            self.log.logger.info(f"Install {commit} dkms deb")
            Pc.execute('sudo dkms remove mtgpu -v 1.0.0 --all')
            Pc.execute('sudo rm -rf /usr/src/mtgpu-1.0.0')
            Pc.execute(f'sudo dpkg -X {fallback_folder}/{commit}_KMD.deb /')
            Pc.execute('sudo dkms add mtgpu -v 1.0.0')
            # dkms build, 安装失败大概率会在这里出错
            Pc.execute('sudo dkms install mtgpu -v 1.0.0')
        rs = Pc.execute("[ ! -e /etc/modprobe.d/mtgpu.conf ] && echo yes || echo no")
        if rs[0] == 'yes':
            Pc.execute("echo -e 'options mtgpu display=mt EnableFWContextSwitch=27'  |sudo tee /etc/modprobe.d/mtgpu.conf")
        Pc.execute("sudo depmod -a && sudo update-initramfs -u")
        # reboot && check kmd version 
        if Pc.reboot_and_reconnect(wait_time=30, retries=10):
            Kmd_Version = self.show_kmd()
            if Kmd_Version in  commit:
                self.log.logger.info(f"安装KMD成功，版本号为 {Kmd_Version}")
                self.log.logger.info('=='*10 + f"Install KMD commit {commit} Complete" + '=='*10)
                return True
            else:
                self.log.logger.error(f"安装KMD {commit}失败, {Kmd_Version=}")
                return False
    
    def install_deb(self,driver,pc=None):
        Pc = self.sshclient
        branch,glvnd,os_type,architecture, exec_user = (
            self.config.branch,
            Pc.info['glvnd'],
            Pc.info['os_type'],
            Pc.info['architecture'],
            Pc.info['exec_user']
        )
        self.log.logger.info('=='*10 + f"Installing  driver {driver}" + '=='*10)
        work_date = re.search(r"\d{4}.\d{2}.\d{2}",driver)
        work_date = work_date.group()
        work_date = datetime.strftime(datetime.strptime(work_date, "%Y.%m.%d"), "%Y%m%d")
        driver_name = f"{driver}+dkms+{glvnd}-{os_type}_{architecture}.deb"
        if pc == 'pc':
            driver_name = f"{driver}+dkms+{glvnd}-{pc}_{architecture}.deb"
        # else:
        #     # driver_name = f"{commit}+dkms+{glvnd}-{os_type}_{architecture}.deb"
        #     driver_name = f"{driver}+dkms+{glvnd}-{os_type}_{architecture}.deb"
        # if work_date > datetime.strptime("20240708","%Y%m%d"):
        #     driver_name = f"{driver}+dkms+{glvnd}-pc_{architecture}.deb"
        print(f"{driver_name=}")
        driver_url = f"https://oss.mthreads.com/product-release/{branch}/{work_date}/{driver_name}"
        fallback_folder = f"/home/{exec_user}/Fallback/DEB_Fallback"
        Pc.wget_url(driver_url,fallback_folder)
        rs = Pc.execute(f"sudo dpkg -P musa && sudo DEBIAN_FRONTEND=noninteractive DEBCONF_NONINTERACTIVE_SEEN=true apt install {fallback_folder}/{driver_name} -y --allow-downgrades && \
                echo 'apt install pass' || echo 'apt install fail'")
        # check  install command run status;  
        if 'apt install fail' in rs:
            self.log.logger.error(f'"apt install {fallback_folder}/{driver_name} -y"执行报错！')
            return False
        self.log.logger.info(f'"apt install {fallback_folder}/{driver_name} -y"执行未报错')
        # 重启,check install version
        if Pc.reboot_and_reconnect(wait_time=30, retries=10):
            deb_version = self.show_deb()
            driver_version = driver.split("musa_")[-1]
            if driver_version in deb_version:
                self.log.logger.info(f"driver安装成功，版本号为 {deb_version}")
                self.log.logger.info('=='*10 + f"Install  driver {driver} Complete" + '=='*10)
                return True
            else:
                self.log.logger.error(f"包 {driver_name} 未安装成功。")
                return False

    def show_kmd(self):
        Pc = self.sshclient
        rs = Pc.execute("lsmod |grep mtgpu")[0]
        if rs:
            Kmd_Version = Pc.execute("modinfo mtgpu |grep build_version |awk '{print $NF}'")[0]
            if Kmd_Version:
                self.log.logger.info(f"{Kmd_Version=}")
        return Kmd_Version

    def show_umd(self):
        Pc = self.sshclient
        Umd_Version = None
        display_var = self.get_display_var()
        if display_var:
            # 通过'OGL version'获取
            Umd_Version = Pc.execute(f"export DISPLAY={display_var} && glxinfo -B |grep -i 'OpenGL version string'|grep -oP '\\b[0-9a-f]{{9}}\\b(?=@)'")[0]
        if  Umd_Version :
            self.log.logger.info(f"{Umd_Version=}")
        return Umd_Version

    def get_display_var(self):
        Pc = self.sshclient
        display_var = Pc.execute(r"who | grep -o '(:[0-9]\+)' | sed 's/[()]//g' |head -n 1")[0]
        if not display_var:
            display_var = Pc.execute(r"w -h  | awk '{print $3}'|grep -o '^:[0-9]\+' |head -n 1")[0]
            if not display_var:
                display_var=':0'
                rs = Pc.execute(f"export DISPLAY={display_var} ; xrandr 2>$1")[0]
                if "Can't open display" in rs:
                    display_var=':1'
                    rs = Pc.execute(f"export DISPLAY={display_var} ; xrandr 2>$1")[0]
                    if "Can't open display" in rs:
                        print("xrandr failed to run with both :0 and :1")
                        return None
        return display_var

    def show_deb(self):
        Pc = self.sshclient
        result = Pc.execute(f"dpkg -s musa")
        deb_version = ''
        for line in result[0].splitlines():
            if "Version: " in line:
                deb_version = line.split("Version: ")[-1]
        if  deb_version:
            self.log.logger.info(f"{deb_version=}")
        return deb_version

if __name__ == "__main__":

    Fallback().find_regression()
    # deb_info_obj = deb_info(branch,begin_date, end_date,Pc_info)
    #     # commit = 'b6ba94c99'
    #     # install_umd(commit,Pc,glvnd,os_type,arch,architecture,dm_type,kernel_version, exec_user)
    #     # commit = 'd8cb481ab'
    #     # install_kmd('d8cb481ab',Pc,glvnd,os_type,arch,architecture,dm_type,kernel_version, exec_user)
    # deb_list = ['musa_2024.07.11-D+375','musa_2024.07.12-D+378']
    # umd_search_list, kmd_search_list = deb_info_obj.get_UMD_KMD_commit_from_deb(deb_list)
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

    # deb_info_obj.get_commit_from_deb_info('musa_2024.07.11-D+375')
