#!/usr/bin/env python3

import os,datetime,time
import logging
from logging.handlers import TimedRotatingFileHandler,RotatingFileHandler

# _baseHome = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_baseHome = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    RESET = '\033[0m'


# 可以尝试使用logura,颜色效果更好
class CustomFormatter(logging.Formatter):

    def format(self, record):
        log_message = super().format(record)
        # if record.levelno == logging.INFO:
        #     return f"{Colors.GREEN}{log_message}{Colors.RESET}"
        if record.levelno >= logging.WARNING:
            return f"{Colors.RED}{log_message}{Colors.RESET}"
        return log_message

class logManager():
    # log_level没法直接用字符串，通过eval执行后，就变成logging定义的对象了
    log_level = eval("logging.DEBUG")
    console_level = eval("logging.INFO")
    log_format = "%(asctime)s - %(name)s - %(filename)s[line:%(lineno)d] - %(levelname)s - %(message)s"
    console_format = "%(message)s"
    log_path = "log"
    def __init__(self, IP, name="main"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level=self.log_level)

        formatter = logging.Formatter(self.log_format)
        console_formatter = CustomFormatter(self.console_format)
        # logging的TimedRotatingFileHandler方法提供滚动输出日志的功能
        now = datetime.datetime.now()
        now = now.strftime("%Y%m%d_%H%M%S")
        IP = logManager.get_ip_suffix(IP)
        _log_file = os.path.join(_baseHome, self.log_path, f"log_{IP}_{now}.txt")
        # _keyinfo_file = os.path.join(_baseHome,self.log_path,f"keyinfo_{IP}.txt")
        if not os.path.exists(_log_file):
            # os.makedirs(self.log_path)
            os.makedirs(os.path.join(_baseHome,self.log_path), exist_ok=True)
            # with open(_log_file,'w') as f:
            #     f.write('')
        # handler = TimedRotatingFileHandler(filename=_log_file, when="D", interval=1, backupCount=7)
        handler = logManager.creat_handler(_log_file,self.log_level,formatter)
        # handler = RotatingFileHandler(filename=_log_file, maxBytes=1024, backupCount=0)
        # handler.setLevel(self.log_level)
        # handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        console = logging.StreamHandler()
        console.setLevel(self.console_level)
        console.setFormatter(console_formatter)
        self.logger.addHandler(console)
    
    @staticmethod
    def get_ip_suffix(ip_address):
        parts = ip_address.split('.')
        return '.'.join(parts[-2:])

    @staticmethod
    def creat_handler(file,log_level,Keyinfo_formatter):
        keyinfo_handler = RotatingFileHandler(filename=file, maxBytes=10*1024*1024, backupCount=0)
        keyinfo_handler.setLevel(log_level)
        keyinfo_handler.setFormatter(Keyinfo_formatter)
        return keyinfo_handler

class KeyInfo_Logging:

    # log_level没法直接用字符串，通过eval执行后，就变成logging定义的对象了
    log_level = eval("logging.INFO")

    log_format = "%(asctime)s - %(name)s - %(filename)s[line:%(lineno)d] - %(levelname)s - %(message)s"
    log_path = "log"
    def __init__(self, IP, name="main"):
        self.keyinfo_logger = logging.getLogger(name)
        self.keyinfo_logger.setLevel(level=self.log_level)
        Keyinfo_formatter = logging.Formatter(self.log_format)
        # console_formatter = CustomFormatter(self.console_format)
        # logging的TimedRotatingFileHandler方法提供滚动输出日志的功能
        now = datetime.datetime.now()
        now = now.strftime("%Y%m%d_%H%M%S")
        IP = logManager.get_ip_suffix(IP)
        # _log_file = os.path.join(_baseHome, self.log_path, f"log_{IP}_{now}.txt")
        _keyinfo_file = os.path.join(_baseHome,self.log_path,f"keyinfo_{IP}.txt")
        if not  not os.path.exists(_keyinfo_file):
            os.makedirs(os.path.join(_baseHome,self.log_path), exist_ok=True)
            # with open(_keyinfo_file,'a') as file:
            #     file.write('')
        # keyinfo_handler = RotatingFileHandler(filename=_keyinfo_file, maxBytes=10*1024*1024, backupCount=0)
        # keyinfo_handler.setLevel(self.log_level)
        # keyinfo_handler.setFormatter(Keyinfo_formatter)
        keyinfo_handler = logManager.creat_handler(_keyinfo_file,self.log_level,Keyinfo_formatter)
        self.keyinfo_logger.addHandler(keyinfo_handler)

    

if __name__ == "__main__":
    log = logManager('192.168.1.2')
    keylog = KeyInfo_Logging('192.168.1.2')
    logger = logging.getLogger('main')
    log.logger.warning('log test----------')
    log.logger.info("This is an info message")
    log.logger.error("This is an error message")
    # keylog.keyinfo_logger.warning("This is an keyinfo_logger warning message")
    # keylog.keyinfo_logger.info("This is an keyinfo_logger info message")
    # keylog.keyinfo_logger.error("This is an keyinfo_logger error message")
    # keylog.keyinfo_logger.critical("This is an keyinfo_logger critical message")
    # print(sys.builtin_module_names)
    # for i in range(10000):  # 这个循环模拟日志记录的过程
    #     log.logger.info(f"This is log message {i+1}")
    #     time.sleep(0.1) 