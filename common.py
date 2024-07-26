#!/usr/bin/python3

import os,time,sys,subprocess,re, json
import sshClient,get_commit
from datetime import datetime, timezone, timedelta
from logManager import logManager
import argparse
from get_deb import deb_info

# common function
# class common():
#     log = logManager('common')
log = logManager('common')

def fallback(component,driver_list,Pc,Pc_info,branch):
    if not driver_list:
        log.logger.error("Get driver_list is empty! Please check driver date!")
        sys.exit(-1)
    elif len(driver_list) == 1 :
        log.logger.info(f"{len(driver_list)=} ; Please check driver date!")
        sys.exit(0)
    log.logger.info(f"{component} {driver_list=}")
    if component == 'deb':
        rs_list = middle_search('deb',driver_list,Pc,Pc_info,branch)
        if not rs_list:
            log.logger.error(f"{driver_list} deb区间无法确定问题引入范围")
            return None
            # sys.exit(-1)
    elif component == 'gr-umd':
        rs_list = middle_search('gr-umd',driver_list,Pc,Pc_info,branch)
        if not rs_list:
            log.logger.error(f"{driver_list} UMD区间无法确定问题引入范围")
            return None
    elif component == 'gr-kmd':
        rs_list = middle_search('gr-kmd',driver_list,Pc,Pc_info,branch)
        if not rs_list:
            log.logger.error(f"{driver_list} KMD区间无法确定问题引入范围")
            return None
    return rs_list

def validate_commit(commit):
    commit_pattern = re.compile(r'^[a-z0-9]{9}$')
    if not commit_pattern.match(commit):
        raise argparse.ArgumentTypeError(f"Invalid commit format: '{commit}'. 每个commit需满足9位包含小写字母数字的字符串")
    return commit

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

def check_url(repo,search_list,branch,arch,glvnd):
    rs = []
    fail_rs = []
    for commit in search_list:
        if repo == 'umd':
            url = f"http://oss.mthreads.com/release-ci/gr-umd/{branch}/{commit}_{arch}-mtgpu_linux-xorg-release-hw.tar.gz"
            if glvnd:
                url = f"http://oss.mthreads.com/release-ci/gr-umd/{branch}/{commit}_{arch}-mtgpu_linux-xorg-release-hw-{glvnd}.tar.gz"
        elif repo == 'kmd':
            url = f"http://oss.mthreads.com/sw-build/gr-kmd/{branch}/{commit}/{commit}_{arch}-mtgpu_linux-xorg-release-hw.deb"
        else:
            work_date = re.search(r"\d{4}.\d{2}.\d{2}",commit)
            work_date = work_date.group()
            work_date = datetime.strptime(work_date, "%Y.%m.%d")
            work_date = datetime.strftime(work_date, "%Y%m%d")
            url = f"https://oss.mthreads.com/product-release/{branch}/{work_date}/{commit}"
        try:
            result = subprocess.run(
                ['wget', '--spider', '-q', url], # --spider 表示不下载，只检查，-q 表示安静模式
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            if result.returncode == 0:
                rs.append(commit)
            else:
                log.logger.error(f"{url}地址不存在，移除{repo} {commit}")
                fail_rs.append(commit)
        except Exception as e:
            log.logger.error(f"An error occurred: {e}")
            # return False
        log.logger.info(f"因oss地址不存在移除{repo}列表{fail_rs}")
    return rs

def get_commit_from_deb(deb_list,branch,arch,glvnd):
    gr_umd_start_end = []
    gr_kmd_start_end = []
    for deb_info in deb_list:
        deb_date = re.search(r'\d{4}\.\d{2}\.\d{2}',deb_info).group()
        log.logger.info(f"{deb_date=}")
        deb_date = datetime.strptime(deb_date,"%Y.%m.%d").strftime("%Y%m%d")
        url = f"https://oss.mthreads.com/release-ci/repo_tags/{deb_date}.txt"
        log.logger.info(f"curl {url}")
        try:
            rs = subprocess.run(['curl', url], capture_output=True, text=True, check=True)
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
    begin_date = re.search(r"\d{4}.\d{2}.\d{2}",deb_list[0]).group()
    end_date = re.search(r"\d{4}.\d{2}.\d{2}",deb_list[1]).group()
    previous_day = datetime.strptime(begin_date,"%Y.%m.%d") - timedelta(days=1)
    # 设置开始时间为前一天12:00，结束时间为当天的23:00
    commit_begin_date = previous_day.replace(hour=12, minute=0, second=0).strftime("%Y-%m-%d %H:%M:%S")
    commit_end_date = datetime.strptime(end_date,"%Y.%m.%d").replace(hour=23,minute=0,second=0).strftime("%Y-%m-%d %H:%M:%S")
    # 格式化输出
    log.logger.info(f"commit查询开始时间：{commit_begin_date}\ncommit查询结束时间：{commit_end_date}\n")    
    umd_list = get_commit.get_git_commit_info("gr-umd", branch, commit_begin_date , commit_end_date)
    kmd_list = get_commit.get_git_commit_info("gr-kmd", branch, commit_begin_date , commit_end_date)
    log.logger.info(f"{umd_list=}\n{kmd_list=}\n")
    umd_search_list , kmd_search_list = slice_full_list(gr_umd_start_end,umd_list) , slice_full_list(gr_kmd_start_end,kmd_list)
    log.logger.info(f"{umd_search_list=}\n{kmd_search_list=}\n")
    umd_search_list,kmd_search_list = check_url("umd",umd_search_list,branch,arch,glvnd),check_url("kmd",kmd_search_list,branch,arch,glvnd)
    return umd_search_list,kmd_search_list

class Config:
    # file_path = "config.json"
    def __init__(self,file_path="config.json") :
        self.file_path=file_path
        self._config_data = self.read_config()
        self.begin_date,self.end_date = self.get_default_dates()
        self.component = self._config_data.get('component',None)
        self.commit_list = self._config_data.get('commit_list',None)
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

def install_deb(driver,Pc,branch,glvnd,os_type,architecture, exec_user):
    log.logger.info('=='*10 + f"Installing  driver {driver}" + '=='*10)
    
    work_date = re.search(r"\d{4}.\d{2}.\d{2}",driver)
    work_date = work_date.group()
    work_date = datetime.strptime(work_date, "%Y.%m.%d")
    driver_name = f"{driver}+dkms+{glvnd}-{os_type}_{architecture}.deb"
    if work_date > datetime.strptime("20240708","%Y%m%d"):
        driver_name = f"{driver}+dkms+{glvnd}-pc_{architecture}.deb"
    print(f"{driver_name=}")
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
        driver_version = driver.split("musa_")[-1]
        if driver_version in deb_version:
            log.logger.info(f"driver安装成功，版本号为 {deb_version}")
            log.logger.info('=='*10 + f"Install  driver {driver} Complete" + '=='*10)
            return True
        elif deb_version != '0' and driver not in deb_version:
            log.logger.error(f"安装{driver}失败，版本号为 {deb_version}")
            return False
        else:
            log.logger.error(f"包 {driver_name} 未安装成功。")
            return False
        
def install_umd(commit,Pc,branch,glvnd,arch,dm_type,exec_user):
    # branch = Config().branch
    log.logger.info('=='*10 + f"Installing UMD commit {commit}" + '=='*10)
    destination_folder = f"/home/{exec_user}/UMD_fallback"
    # 下载
    if glvnd == 'glvnd':
        UMD_commit_URL = f"http://oss.mthreads.com/release-ci/gr-umd/{branch}/{commit}_{arch}-mtgpu_linux-xorg-release-hw-{glvnd}.tar.gz"
    else:
        UMD_commit_URL = f"http://oss.mthreads.com/release-ci/gr-umd/{branch}/{commit}_{arch}-mtgpu_linux-xorg-release-hw.tar.gz"
    
    rs = wget_url(Pc,UMD_commit_URL,destination_folder,f"{commit}_UMD.tar.gz")
    if not rs:
        return False
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

def install_kmd(commit,Pc,branch,arch,dm_type,kernel_version, exec_user):
    # Download KMD tar or dkms-deb
    # KMD_commit_URL = f"http://oss.mthreads.com/sw-build/gr-kmd/{branch}/{commit}/{commit}_{arch}-mtgpu_linux-xorg-release-hw.tar.gz"
    # # https://oss.mthreads.com/sw-build/gr-kmd/develop/7a52195ed/7a52195ed_x86_64-mtgpu_linux-xorg-release-hw.tar.gz
    # destination_folder = f"/home/{exec_user}/KMD_fallback"
    # rs = wget_url(Pc,KMD_commit_URL,destination_folder,f"{commit}_KMD.tar.gz")
    # if not rs:
    #     return False
    # Pc.execute(f"cd {destination_folder} && mkdir -p {destination_folder}/{commit}_KMD && tar -xvf {commit}_KMD.tar.gz -C {destination_folder}/{commit}_KMD")
    # rs = Pc.execute("cd %s && find %s_KMD -name mtgpu.ko | awk -F '/' '{print $(NF-2)}' " % (destination_folder,commit))
    # if rs[0] != kernel_version:
    #     log.logger.info(f"下载的{commit}_KMD.tar.gz与{kernel_version}不匹配")
    #     KMD_commit_URL = f"http://oss.mthreads.com/sw-build/gr-kmd/{branch}/{commit}/{commit}_{arch}-mtgpu_linux-xorg-release-hw.deb"
    #     Pc.execute(f"rm -rf {destination_folder}/{commit}_KMD*")
    #     rs = wget_url(Pc,KMD_commit_URL,destination_folder,f"{commit}_KMD.deb")
    #     if not rs:
    #         return False
    # branch = Config().branch
    log.logger.info('=='*10 + f"Installing KMD commit {commit}" + '=='*10)
    destination_folder = f"/home/{exec_user}/KMD_fallback"    
    if (kernel_version == '5.4.0-42-generic' and  arch == 'x86_64') or (kernel_version == '5.4.18-73-generic' and  arch == 'arm64'):
        KMD_commit_URL = f"http://oss.mthreads.com/sw-build/gr-kmd/{branch}/{commit}/{commit}_{arch}-mtgpu_linux-xorg-release-hw.tar.gz"
        rs = wget_url(Pc,KMD_commit_URL,destination_folder,f"{commit}_KMD.tar.gz")
        if not rs:
            return False
    else:
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
        Pc.execute(f"cd {destination_folder} && mkdir -p {destination_folder}/{commit}_KMD && tar -xvf {commit}_KMD.tar.gz -C {destination_folder}/{commit}_KMD")
        Pc.execute("[ -e /lib/modules/`uname -r`/updates/dkms/mtgpu.ko ] && \
                            sudo mv /lib/modules/`uname -r`/updates/dkms/mtgpu.ko /lib/modules/`uname -r`/updates/dkms/mtgpu.ko.bak")
        Pc.execute("[ ! -d /lib/modules/`uname -r`/extra/ ] && sudo mkdir -p /lib/modules/`uname -r`/extra/ ")
        Pc.execute(f"cd {destination_folder} && \
                    sudo cp $(find {commit}_KMD/{arch}-mtgpu_linux-xorg-release/ -name mtgpu.ko) /lib/modules/`uname -r`/extra/")
    else:
        log.logger.info(f"Install {commit} dkms deb")
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
                log.logger.info(f"安装KMD成功，版本号为 {Kmd_Version}")
                log.logger.info('=='*10 + f"Install KMD commit {commit} Complete" + '=='*10)
                return True
            else:
                log.logger.error(f"安装KMD {commit}失败, {Kmd_Version=}")
                return False
        else:
            log.logger.error(f"kmd no load present !!!")
            return False

def install_driver(repo,driver,Pc,Pc_info,branch):
    if repo == 'deb':
        rs = install_deb(driver,Pc,branch,Pc_info.glvnd,Pc_info.os_type,Pc_info.architecture, Pc_info.exec_user)
    elif repo == 'gr-umd':
        rs = install_umd(driver,Pc,branch,Pc_info.glvnd,Pc_info.arch,Pc_info.dm_type, Pc_info.exec_user)
    elif repo == 'gr-kmd':
        rs = install_kmd(driver,Pc,branch,Pc_info.arch,Pc_info.dm_type,Pc_info.kernel_version, Pc_info.exec_user)
    return testcase()
    # test_result = ''
    # if not rs:
    #     test_result = 'fail'
    #     return test_result
    # else:
    #     test_result = testcase()
    #     return test_result

def testcase():
    rs = input("请手动测试后输入测试结果：pass/fail\n")
    return rs

# 二分查找
def middle_search(repo,middle_search_list,Pc,Pc_info,branch):
    # left、right初始值为列表元素的序号index 最小值和最大值
    left = 0 
    right = len(middle_search_list) - 1
    count = 1
    # left_value = "pass"
    right_value =  "fail"
    left_value = install_driver(repo,middle_search_list[left],Pc,Pc_info,branch)
    # right_value = install_driver(repo,middle_search_list[right],Pc)
    # if left_value == right_value:
    #     log.logger.info(f"{middle_search_list}区间内第一个元素和最后一个的结果相同，请确认区间范围")
    #     return None               
    while left <= right -2 :
        middle = (left + right )//2 
        count += 1 
        mid_value = install_driver(repo,middle_search_list[middle],Pc,Pc_info,branch)
        if mid_value != None and mid_value == left_value:
            left = middle 
        elif mid_value != None and mid_value == right_value:
            right = middle 
    log.logger.info(f"总共{count}次查找\n\n定位到问题引入范围是：\"{middle_search_list[left]}\"(不发生)-\"{middle_search_list[right]}\"(发生)之间引入") 
    return middle_search_list[left:right]

def run(component=None,commit_list=None):
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
    Pc = sshClient.sshClient(Test_Host_IP,Host_name,passwd)
    Pc_info = Pc_Info(Pc)
    print(f"{config.component=}")
    print(f"{Pc_info.os_type=}")
    if component and commit_list:
        if component == 'umd':
            fallback('gr-umd',commit_list,Pc,Pc_info,branch)
        else:
            fallback('gr-kmd',commit_list,Pc,Pc_info,branch)
    else:
        # 获取deb 列表
        driver_list = deb_info(branch,begin_date, end_date).get_deb_version() 
        print(f"{driver_list=}")
        deb_rs_list = fallback('deb',driver_list,Pc,Pc_info,branch)
        umd_search_list, kmd_search_list = get_commit_from_deb(deb_rs_list,branch,Pc_info.arch,Pc_info.glvnd)
        print(f"{umd_search_list=}\n{kmd_search_list=}")
        if not fallback('gr-umd',umd_search_list,Pc,Pc_info,branch): 
            fallback('gr-kmd',kmd_search_list,Pc,Pc_info,branch)

# if __name__ == "__main__":
#     config = Config()
#     print(f"Begin date: {config.component}")

if __name__ == "__main__":
    branch = 'develop'
    begin_date = '20240711'
    end_date = '20240712'
    Test_Host_IP = '192.168.115.207'
    Host_name = 'swqa'
    passwd = 'gfx123456'
    # Test_Host_IP = '192.168.2.131'
    # Host_name = 'georgy'
    # passwd = '123456'
    Pc = sshClient.sshClient(Test_Host_IP,Host_name,passwd)
    rs = Pc_Info(Pc)
    print(f"{rs.arch=}")
    print(f"{Config().begin_date}")
        # commit = 'b6ba94c99'
        # install_umd(commit,Pc,glvnd,os_type,arch,architecture,dm_type,kernel_version, exec_user)
        # commit = 'd8cb481ab'
        # install_kmd('d8cb481ab',Pc,glvnd,os_type,arch,architecture,dm_type,kernel_version, exec_user)
    # deb_list = ['musa_2024.07.11-D+375','musa_2024.07.12-D+378']
    # umd_search_list,kmd_search_list = get_commit_from_deb(deb_list,branch,arch,glvnd)
    # print(f"{umd_search_list=}\n{kmd_search_list=}")