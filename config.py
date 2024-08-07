#!/usr/bin/python3
import argparse,os,sys
from datetime import timedelta,datetime 
import json,re

class Config:
    # file_path = "config.json"
    def __init__(self) :
        self.file_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
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
        parser.add_argument('-i','--commit_list',nargs=2, type=Config.validate_commit, help="需输入两笔commit:'commit_pass' 'commit_fail'")
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

    @staticmethod
    def validate_commit(commit):
        commit_pattern = re.compile(r'^[a-z0-9]{9}$')
        if not commit_pattern.match(commit):
            raise argparse.ArgumentTypeError(f"Invalid commit format: '{commit}'. 每个commit需满足9位包含小写字母数字的字符串")
        return commit