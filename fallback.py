#!/usr/bin/python3
from get_deb import deb_info
import sys,re
import sshClient
from logManager import logManager
import common
from common import fallback

log = logManager('fallback')

def main(component=None,commit_list=None):
    config = common.Config()
    Test_Host_IP,Host_name,passwd,branch,begin_date,end_date = (
    config.Test_Host_IP,
    config.Host_name,
    config.passwd,
    config.branch,
    config.begin_date,
    config.end_date
    )
    Pc = sshClient.sshClient(Test_Host_IP,Host_name,passwd)
    Pc_info = common.Pc_Info(Pc)
    if component and commit_list:
        if component == 'umd':
            fallback('gr-umd',commit_list,Pc)
        else:
            fallback('gr-kmd',commit_list,Pc)
    else:
        # 获取deb 列表
        driver_list = deb_info(branch,begin_date, end_date).get_deb_version() 
        deb_rs_list = fallback('deb',driver_list,Pc)
        umd_search_list, kmd_search_list = common.get_commit_from_deb(deb_rs_list,branch,Pc_info.arch,Pc_info.glvnd)
        print(f"{umd_search_list=}\n{kmd_search_list=}")
        if not fallback('gr-umd',umd_search_list,Pc): 
            fallback('gr-kmd',kmd_search_list,Pc)

if __name__ == "__main__":
    
    # 如果命令行参数提供了 begin_date 或 end_date，则覆盖配置文件中的值
    args= common.args()
    if args.begin_date:
        begin_date = args.begin_date
    if args.end_date:
        end_date = args.end_date
    if args.component:
        component = args.component
        if  args.commit_list:
            commit_list =args.commit_list
        # main(config,component,commit_list) 
    else:
        # main(config)
        print(f"{common.Config().begin_date}")