#!/usr/bin/python3
import os,sys,time
import datetime
import pandas as pd
import subprocess


def deal(begin_date, end_date):
    date_list = []
    begin_date = datetime.datetime.strptime(begin_date, "%Y%m%d")
    end_date = datetime.datetime.strptime(end_date, "%Y%m%d")
    while begin_date <= end_date:
        date_str = begin_date.strftime("%Y%m%d")
        date_list.append(date_str)
        begin_date += datetime.timedelta(days=1)
    # print(date_list)
    work_date_list = []
    # begin_time和end_time之间日期的 去除周末的日期
    for i in date_list:
        i = datetime.datetime.strptime(i,"%Y%m%d")
        if i.weekday() < 5 :
            work_date_list.append(i.strftime("%Y%m%d"))
    print(work_date_list)
    return work_date_list

def get_deb_version(branch,begin_date,end_date):
    result = []
    work_date_list = deal(begin_date, end_date)
    
    for work_date in work_date_list:
        rs = subprocess.Popen(f"curl https://oss.mthreads.com/product-release/{branch}/{work_date}/daily_build.txt", shell=True, close_fds=True, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE, preexec_fn = os.setsid).communicate()
        # output = subprocess.Popen(f"curl https://oss.mthreads.com/product-release/{branch}/{work_date}/daily_build.txt",stdout=subprocess.PIPE,shell=True).communicate()
        # print(rs[0])
        rs =  rs[0].decode().strip()
        out_list = rs.splitlines()
        # result[work_date] = []
        # print(out_list)
        result.append(out_list)
        # result[work_date].append(out_list[1]) 
    # for work_date,driver_version in result.items():
    #     driver_name = f"{driver_version[0]}+dkms+glvnd-Ubuntu_amd64.deb"
    #     driver_url = f"https://oss.mthreads.com/product-release/{branch}/{work_date}/{driver_name}"
    #     result[work_date].append(driver_url)
    #     result[work_date].append(driver_name)
    print(result)
    return result



if __name__ == '__main__':
    driver_dic = get_deb_version('develop','20240326', '20240327')
    Test_Host_IP = "192.168.114.55"
    # install_driver(driver_dic,Test_Host_IP)