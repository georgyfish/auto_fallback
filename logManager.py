#!/usr/bin/env python3

import os, sys
import logging
from logging.handlers import TimedRotatingFileHandler

# _baseHome = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_baseHome = os.path.dirname(os.path.abspath(__file__))

class logManager():
    # log_level没法直接用字符串，通过eval执行后，就变成logging定义的对象了
    log_level = eval("logging.DEBUG")
    log_format = "%(asctime)s - %(name)s - %(filename)s[line:%(lineno)d] - %(levelname)s - %(message)s"
    log_path = "log"

    def __init__(self, name="main"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level=self.log_level)
        formatter = logging.Formatter(self.log_format)
        # logging的TimedRotatingFileHandler方法提供滚动输出日志的功能
        _log_file = os.path.join(_baseHome, self.log_path, "log.txt")
        if not os.path.exists(_log_file):
            # os.makedirs(self.log_path)
            os.makedirs(os.path.join(_baseHome,self.log_path), exist_ok=True)
            with open(_log_file,'w') as f:
                f.write('')
        handler = TimedRotatingFileHandler(filename=_log_file, when="D", interval=1, backupCount=7)
        handler.setLevel(self.log_level)
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        console = logging.StreamHandler()
        console.setLevel(self.log_level)
        console.setFormatter(formatter)
        self.logger.addHandler(console)

if __name__ == "__main__":
    log = logManager()
    # logger = logging.getLogger('main')
    log.logger.info('log test----------')
    print(sys.builtin_module_names)