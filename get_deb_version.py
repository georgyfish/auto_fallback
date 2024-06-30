#!/usr/bin/python3
import os,sys,time
import datetime
import subprocess
from logManager import logManager

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
    # print(work_date_list)
    return work_date_list

def get_deb_version(branch,begin_date,end_date):
    result = []
    work_date_list = deal(begin_date, end_date)
    log = logManager('get_deb_version')
    # error
    for work_date in work_date_list:
        url = f"https://oss.mthreads.com/product-release/{branch}/{work_date}/daily_build.txt"
        log.logger.info(f"curl {url}")
        try:
            rs = subprocess.run(['curl', url], capture_output=True, text=True, check=True)
            stdout_list = rs.stdout.splitlines()
            log.logger.info(f"{stdout_list=}")
            result.append(stdout_list)
        except subprocess.CalledProcessError as e:
        # 打印错误信息
            log.logger.error(f"Error:\n{e.stderr}")
        except Exception as e:
        # 处理其他异常
            log.logger.error(f"An unexpected error occurred: {e}")
    return result



if __name__ == '__main__':
    driver_full_list = get_deb_version('develop','20240528', '20240601')
    print(driver_full_list)
    # log = logManager('get_deb_version')
    # result = []
    # try:
    #     rs = subprocess.run(['curl', "https://mirror.ghproxy.com/https://raw.githubusercontent.com/georgyfish/test_script/main/1.txt"], capture_output=True, text=True, check=True)
    #     # print("Output:", rs.stdout)
    #     stdout_list = rs.stdout.splitlines()
    #     log.logger.info(f"{stdout_list=}")
    #     result.append(stdout_list)
    # except subprocess.CalledProcessError as e:
    # # 打印错误信息
    #     # print("Error:\n", e.stderr)
    #     log.logger.error(f"Error:\n{e.stderr}")
    # except Exception as e:
    # # 处理其他异常
    #     print(f"An unexpected error occurred: {e}")
    # print(result)