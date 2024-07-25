#!/usr/bin/python3
from get_deb import deb_info
import sys
import sshClient
from logManager import logManager
import common
from datetime import datetime,timedelta
import argparse


log = logManager('fallback')

def deb_fallback(driver_list,Pc):
    if not driver_list:
        log.logger.error("Get driver_list is empty! Please check driver date!")
        sys.exit(-1)
    elif len(driver_list) == 1 :
        log.logger.info(f"{len(driver_list)=} ; Please check driver date!")
        sys.exit(0)
    log.logger.info(f"{driver_list=}")
    deb_rs_list = common.middle_search('deb',driver_list,Pc)
    if not deb_rs_list:
        log.logger.error(f"{driver_list} deb区间无法确定问题引入范围")
        sys.exit(-1)
    return deb_rs_list

def umd_fallback(umd_search_list,Pc):
    umd_rs_list = common.middle_search('gr-umd',umd_search_list,Pc)
    if not umd_rs_list:
        log.logger.error(f"{umd_search_list} UMD区间无法确定问题引入范围")
        # sys.exit(-1)
    return umd_rs_list

def kmd_fallback(kmd_search_list,Pc):
    kmd_rs_list = common.middle_search('gr-kmd',kmd_search_list,Pc)
    if not kmd_rs_list:
        log.logger.error(f"{kmd_search_list} 此KMD区间无法确定问题引入范围")
        sys.exit(-1)
    return kmd_rs_list

# def main(begin_date,end_date,Pc,glvnd,os_type,arch,architecture,dm_type,kernel_version, exec_user):
def main(config,component=None,commit_list=None):
    Test_Host_IP,Host_name,passwd,branch,begin_date,end_date = (
    config['Test_Host_IP'],
    config['Host_name'],
    config['passwd'],
    config['branch'],
    config['begin_date'],
    config['end_date']
    )
    print(f"{config=}")
    Pc = sshClient.sshClient(Test_Host_IP,Host_name,passwd)
    # if 1000 == Pc.login():
    rs = common.get_Pc_info(Pc)
    print(f"{rs=}")
    glvnd,os_type,arch,architecture,dm_type,kernel_version, exec_user= (
        rs['glvnd'],
        rs['os_type'],
        rs['arch'],
        rs['architecture'],
        rs['dm_type'],
        rs['kernel_version'],
        rs['exec_user']
    )
    # 获取deb 列表
    deb_list = deb_info(branch,begin_date, end_date)
    driver_list = deb_list.get_deb_version() 
    # print(f"{deb_list.deal(begin_date, end_date)}")

    

    # if component and commit_list:
    #     if component == 'umd':
    #         umd_fallback(commit_list,Pc)
    #     else:
    #         kmd_fallback(commit_list,Pc)
    # else:
    #     deb_rs_list = deb_fallback(driver_list,Pc)
    #     umd_search_list, kmd_search_list = common.get_commit_from_deb(deb_rs_list,driver_full_list,branch,arch,glvnd)
    #     print(f"{umd_search_list=}\n{kmd_search_list=}")
    #     if not umd_fallback(umd_search_list,Pc): 
    #         kmd_fallback(kmd_search_list,Pc)

def args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--begin_date', type=str, help='The beginning date in YYYYMMDD format')
    parser.add_argument('--end_date', type=str, help='The ending date in YYYYMMDD format')
    parser.add_argument('-c','--component',type=str,choices = ['umd','kmd'],help="The component in ['umd','kmd']")
    parser.add_argument('-i','--commit_list',nargs='+',type=str,help="The commit_list in ['commita','commitb', ...] format")
    args = parser.parse_args()
    if args.begin_date:
        config['begin_date'] = args.begin_date
    if args.end_date:
        config['end_date'] = args.end_date
    if args.component:
        if not args.commit_list:
            parser.error("'-c'/'--component' option requires '-i'/'--commit_list'")
    return    args


if __name__ == "__main__":
    config = common.read_config("config.json")
    # 如果命令行参数提供了 begin_date 或 end_date，则覆盖配置文件中的值
    args= args()
    if args.begin_date:
        config['begin_date'] = args.begin_date
    if args.end_date:
        config['end_date'] = args.end_date
    if args.component:
        component = args.component
        if  args.commit_list:
            commit_list =args.commit_list
        main(config,component,commit_list) 
    else:
        main(config)