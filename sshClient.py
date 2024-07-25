#!/usr/bin/env python3

import paramiko,logging,sys,time
from paramiko import AuthenticationException
from logManager import logManager
from paramiko.ssh_exception import SSHException, NoValidConnectionsError

class sshClient():

    def __init__(self, hostname, username, password, port=22):
        self.client = paramiko.SSHClient()
        # self.client = None
        self.log = logManager('ssh')
        self.host = hostname       #连接的目标主机
        self.port = port      #指定端口
        self.user = username      #验证的用户名
<<<<<<< HEAD
        self.passwd = password      #验证的用户密码
        self.login()
=======
        self.passwd = password
        self.login()      #验证的用户密码
>>>>>>> 18f124686847e7046c21218242e3caf810dc4040

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

if __name__ == '__main__':
<<<<<<< HEAD
    Pc = sshClient("192.168.114.55","swqa","gfx123456")
    # if 1000 == Pc.login():
    Umd_Version = Pc.execute("export DISPLAY=:0.0 && glxinfo -B |grep -i 'OpenGL version string'|grep -oP '\\b[0-9a-f]{9}\\b(?=@)'")[0]
    print(f"{Umd_Version=}")
=======
    Pc = sshClient("192.168.2.131","georgy","123456")
    Structure = Pc.execute("uname -m")[0]
    print(f"{Structure=}")
    # if 1000 == Pc.login():
    #     Structure = Pc.execute("uname -m")[0]
    #     print(f"{Structure=}")
>>>>>>> 18f124686847e7046c21218242e3caf810dc4040
        # Pc.execute("echo -e /usr/lib/$(uname -m)-linux-gnu/musa |sudo tee /etc/ld.so.conf.d/00-mtgpu.conf")