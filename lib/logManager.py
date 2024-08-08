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
        # formatter = logging.Formatter(self.log_format)
        formatter = CustomFormatter(self.log_format)
        console_formatter = CustomFormatter(self.console_format)
        # logging的TimedRotatingFileHandler方法提供滚动输出日志的功能
        now = datetime.datetime.now()
        now = now.strftime("%Y%m%d_%H%M%S")
        _log_file = os.path.join(_baseHome, self.log_path, f"log_{IP}_{now}.txt")
        if not os.path.exists(_log_file):
            # os.makedirs(self.log_path)
            os.makedirs(os.path.join(_baseHome,self.log_path), exist_ok=True)
            with open(_log_file,'w') as f:
                f.write('')
        # handler = TimedRotatingFileHandler(filename=_log_file, when="D", interval=1, backupCount=7)
        handler = RotatingFileHandler(filename=_log_file, maxBytes=1024, backupCount=0)
        handler.setLevel(self.log_level)
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        console = logging.StreamHandler()
        console.setLevel(self.console_level)
        console.setFormatter(console_formatter)
        self.logger.addHandler(console)

if __name__ == "__main__":
    log = logManager('192.168.1.2')
    # logger = logging.getLogger('main')
    log.logger.warning('log test----------')
    log.logger.info("This is an info message")
    log.logger.error("This is an error message")
    # print(sys.builtin_module_names)
    for i in range(10000):  # 这个循环模拟日志记录的过程
        log.logger.info(f"This is log message {i+1}")
        time.sleep(0.1) 