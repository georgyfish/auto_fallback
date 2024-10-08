#!/usr/bin/env python3

import paramiko,sys,time,os
from paramiko import AuthenticationException
from paramiko.ssh_exception import SSHException, NoValidConnectionsError
import datetime,re
basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(basedir)
from lib.logManager import logManager


class sshClient():

    def __init__(self, hostname, username, password, port=22):
        self.client = paramiko.SSHClient()
        # self.client = None
        self.log = logManager(hostname,'ssh')
        self.host = hostname       #连接的目标主机
        self.port = port      #指定端口
        self.user = username      #验证的用户名
        self.passwd = password
        self.login()      #验证的用户密码
        self.info = self.get_pc_info()

    def login(self, timeout=10):
        
        try:
            self.log.logger.info(f"Connect to '{self.user}@{self.host}/{self.port}' PassWd: {self.passwd}")
            # 设置允许连接known_hosts文件中的主机（默认连接不在known_hosts文件中的主机会拒绝连接抛出SSHException）
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.client.connect(self.host, port=self.port, username=self.user, password=self.passwd, timeout=timeout)
        except AuthenticationException:
            self.log.logger.error("username or password error")
            return 1001
        except NoValidConnectionsError:
            self.log.logger.error(f"Unable to connect to {self.host}/{self.port}")
            return 1002
        except:
            # print("Unexpected error:", sys.exc_info()[0])
            self.log.logger.error(f"Unexpected error: {sys.exc_info()[0]}")
            return 1003
        return 1000
    
    def execute(self, command,timeout=10):
        if not self.client:
            self.login()
        try:
            if self.client:
                self.log.logger.info(f'Execute "{command}"')
                stdin, stdout, stderr = self.client.exec_command(command)
                Output,Error= stdout.read().decode().strip('\n'), stderr.read().decode()
                self.log.logger.info(f"{Output}")
                if Error:
                    self.log.logger.warning(f"执行如下命令出错:{command}")
                    self.log.logger.warning(f"Error: \n{Error}")
                return  Output,Error
        except SSHException as e:
            self.log.logger.error(f"SSH command execution error: {e}")
            self.login()
            if self.client:
                stdin, stdout, stderr = self.client.exec_command(command)
                Output,Error= stdout.read().decode().strip('\n'), stderr.read().decode()
                self.log.logger.info(f"Output: \n{Output}")
                if Error:
                    self.log.logger.error(f"执行如下命令出错:{command}")
                    self.log.logger.error(f"Error: \n{Error}")
                return  Output,Error
    
    def close(self):
        if self.client:
            self.client.close()
            self.log.logger.info(f"Close connect '{self.host}/{self.port}'")

    def reboot_and_reconnect(self, wait_time=60, retries=10):
        self.log.logger.info(f"Rebooting the remote PC {self.host}...")
        self.execute("sudo reboot")
        self.close()
        
        for attempt in range(retries):
            self.log.logger.info(f"Attempt {attempt + 1} to reconnect after reboot...")
            time.sleep(wait_time)  # Wait for the server to reboot
            
            try:
                self.login()
                if self.client:
                    self.log.logger.info("Reconnected successfully.")
                    return True
            except (SSHException, NoValidConnectionsError) as e:
                self.log.logger.info(f"Reconnect attempt failed: {e}")
        
        self.log.logger.info("Failed to reconnect after reboot.")
        return False

    def logout(self):
        self.log.logger.info(f"Close connect '{self.host}/{self.port}'")
        self.close()

    def get_pc_info(self):
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
            result[key] = self.execute(command)[0]
        result['glvnd'] = 'glvnd'
        if result['arch'] == 'aarch64':
            result['arch'] = 'arm64'
        return result
    
    def wget_url(self,url,local_path=None,file_name=None):
        if not file_name :
            file_name = url.split('/')[-1]
        if local_path:
            destination = f"{local_path}/{file_name}"
            self.execute(f"[ ! -d {local_path} ] && mkdir -p {local_path}")
            rs = self.execute(f"wget --no-check-certificate  {url} -O {destination} && echo 'True' ||echo 'False'")[0]
        else:
            rs = self.execute(f"wget --no-check-certificate  {url} && echo 'True' ||echo 'False'")[0]
        if rs == 'False' :
            self.log.logger.error(f"Download {url} failed !!!")
            # log.logger.error(f"package {file_name} 下载失败！！！")
            return False
        else:
            self.log.logger.info(f"Download {url} success !!!")
            return True 

    def check_path(self,path):
        rs = self.execute(f"ls {path} && echo 'True' || echo 'False'")[0]
        if rs == 'False':
            return False
        else:
            return True


if __name__ == '__main__':
    # Pc = sshClient("192.168.114.55","swqa","gfx123456")
    Pc = sshClient("192.168.2.131","georgy","123456")
    # s = Pc.execute('ls /home/georgy/xc_tool/driver/tmp/')
    stdin, stdout, stderr = Pc.client.exec_command('cat /home/georgy/xc_tool/driver/tmp/1/1')
    print(f"{stdout.read().decode()=}")
    
    # if Pc.check_path("/home/georgy/xc_tool/driver/tmp/"):
    #     print("HHHH")
    # else:
    #     print("FUCK")
    # if 1000 == Pc.login():
    # display_var = Pc.execute("w -h  | awk '{print $3}'|grep -o '^:[0-9]\+' |head -n 1")[0]
    # # Umd_Version = Pc.execute(f"export DISPLAY={display_var} && glxinfo -B |grep -i 'OpenGL version string'|grep -oP '\\b[0-9a-f]{9}\\b(?=@)'")[0]
    # Umd_Version = Pc.execute(f"export DISPLAY={display_var} && glxinfo -B |grep -i 'OpenGL version string'|grep -oP '\\b[0-9a-f]{{9}}\\b(?=@)'")[0]
    
    # # rs = Pc.execute(f"export DISPLAY= ; xrandr 2>&1")
    # print(f"{Umd_Version=}")
    # print(Pc.info)
        # Pc.execute("echo -e /usr/lib/$(uname -m)-linux-gnu/musa |sudo tee /etc/ld.so.conf.d/00-mtgpu.conf")