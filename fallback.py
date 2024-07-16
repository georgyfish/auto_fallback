#!/usr/bin/python3
from get_deb_version import get_deb_version
import sys
import sshClient
from logManager import logManager
import common


def deb_fallback(driver_list,Pc):
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

def main(begin_date,end_date,Pc,glvnd,os_type,arch,architecture,dm_type,kernel_version, exec_user):
    driver_full_list = get_deb_version(branch,begin_date, end_date) 
    driver_list = []
    if not driver_full_list:
        log.logger.error("Get driver_full_list is empty! Please check driver date!")
        sys.exit(-1)
    elif len(driver_full_list) == 1 :
        log.logger.info(f"{len(driver_full_list)=} ; Please check driver date!")
    for driver in driver_full_list:
        driver_version = driver[0]
        driver_list.append(driver_version)
    log.logger.info(f"{driver_list=}")
    deb_rs_list = deb_fallback(driver_list,Pc)
    umd_search_list, kmd_search_list = common.get_commit_from_deb(deb_rs_list,driver_full_list,branch,commit,arch,glvnd)
    print(f"{umd_search_list=}\n{kmd_search_list=}")
    if not umd_fallback(umd_search_list,Pc): 
        kmd_fallback(kmd_search_list,Pc)

if __name__ == "__main__":
    branch = 'develop'
    begin_date = '20240711'
    end_date = '20240712'
    Test_Host_IP = '192.168.114.102'
    Host_name = 'swqa'
    passwd = 'gfx123456'
    log = logManager('Fallback Test')
    Pc = sshClient.sshClient(Test_Host_IP,Host_name,passwd)
    if 1000 == Pc.login():
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
        main(begin_date,end_date,Pc,glvnd,os_type,arch,architecture,dm_type,kernel_version, exec_user)


