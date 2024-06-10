#!/usr/bin/python3
from datetime import datetime, timezone, timedelta
import middle_search
from get_deb_version import get_deb_version
import subprocess,os,sys,get_commit
from sshClient import sshClient
from logManager import logManager
import re

"""
确定发生一个回退问题----》大致版本区间---》根据
1. 根据时间区间拿到deb大致区间   给定一个时间区间参数，分支参数；
    test.py develop 20240501(不发生) 2023040520(发生)
    根据时间参数--找到中间的工作日期  
    根据工作日期对应的daily_deb   
        curl --insecure https://oss.mthreads.com/product-release/develop/20240527/daily_build.txt
        f"curl --insecure https://oss.mthreads.com/product-release/{branch}/{daily_tag}/daily_build.txt"
        result = get_deb_version.get_deb_version(branch,begin_date,end_date)
        [['musa_2024.03.26-D+10129', 'https://oss.mthreads.com/release-ci/repo_tags/20240326.txt'],
          ['musa_2024.03.27-D+10151', 'https://oss.mthreads.com/release-ci/repo_tags/20240327.txt']]

2. 二分法定位:  执行deb -----> 拿到测试结果------->写入字典--->判断   ------> 继续执行deb安装-----> 拿到测试结果------->写入字典------>
判断   结束  -- 得到deb引入区间
    二分查找法，根据嵌套列表的index次序 
        每次去安装查找的那个包 得到结果 写入result 列表
        middle_search 返回一个列表[left.right], left为不发生的index , right为发生的index
    远程控制， 安装驱动deb 
    install_deb()

3. 根据deb 区间  定位到UMD、KMD commit区间 
    result[left][1] = 'https://oss.mthreads.com/release-ci/repo_tags/20240326.txt'
    result[left][2] = 'https://oss.mthreads.com/release-ci/repo_tags/20240327.txt'
    curl 'https://oss.mthreads.com/release-ci/repo_tags/20240326.txt'  ---》 {"mthreads-gmi":{"develop":"15d1e9380","master":"8ee556f92"},"mt-pes":{"master":"7202a31dc"},"mt-management":\
        {"develop":"dad852321","master":"6c374091d"},"mt-media-driver":{"develop":"7e4ecb1cc"},"DirectStream":{"develop":"208e5240d"},"gr-kmd":{"develop":"69d7e3104",\
            "release-2.5.0-OEM":"8c51763a1"},"graphics-compiler":{"master":"545ffa3a9"},"m3d":{"master":"a9567d601"},"mtdxum":{"master":"9cac086dd"},"d3dtests":{"master":"bd0358ed2"},\
                "ogl":{"master":"44be1b68a"},"gr-umd":{"develop":"6dd19a265","release-2.5.0-OEM":"27a85ebf5"},"wddm":{"develop":"d23c6060d"}}
    字典嵌套字典  
        dict['gr-umd']["develop"]  ---> UMD commitID


4. 定位UMD commit引入
    获取UMD commitID 列表
    方法一：
        爬取commit网页，修改begin时间和end时间，筛选出一个umd_commit list，再根据第3步获取的区间，截取、切片找到需要的umd_commit_list；
    方法二：
        使用get_lib.get_git_commit_info() 获取所有的git commit信息，再写一个根据第3步获取的区间得到需要的umd_commit_list的方法；
    

5. UMD定位不到  执行KMD定位

定位umd_commit:
1. get_commit   commit_begin  commit_end
2. middle_search()----> 区间

"""

def get_deb_section(branch, begin_time,end_time):
    result = []
    return result

# 根据deb version拿到umd、kmd区间

# branch = 'develop'
# driver_dic = {'musa_2024.03.26-D+10129': 'https://oss.mthreads.com/release-ci/repo_tags/20240326.txt', 'musa_2024.03.27-D+10151': 'https://oss.mthreads.com/release-ci/repo_tags/20240326.txt'}



def slice_full_list(start_end_list, full_list):
    if start_end_list[0] in full_list:
        index_start = full_list.index(start_end_list[0])
    else:
        print("input error!")
        sys.exit(-1)
    if start_end_list[1] in full_list:
        index_end = full_list.index(start_end_list[1])
    else:
        print("input error!")
        sys.exit(-1)        
    return full_list[index_start:index_end+1]

def main(branch,begin_date,end_date,Pc):
    driver_full_list = get_deb_version(branch,begin_date, end_date) 
    driver_list = []
    for driver in driver_full_list:
        driver_version = driver[0]
        driver_list.append(driver_version)
    # print(driver_list)
    deb_rs_list = deb_fallback(driver_list,Pc)
    # deb_rs_list = ['musa_2024.05.28-D+11235', 'musa_2024.05.29-D+11244']
    if not deb_rs_list:
        print("此deb区间无法确定到问题引入范围")
        sys.exit(-1)

    umd_search_list, kmd_search_list = get_commit_from_deb(deb_rs_list,driver_full_list)
        # {'mthreads-gmi': {'develop': '775306fcc', 'master': 'b55a66c9d'}, 'mt-media-driver': {'develop': '2a48bb594'}, 'mt-pes': {'master': 'ff3b990ba'}, 'gr-kmd': {'develop': 'cfb671a2d',\
        #  'release-2.5.0-OEM': '6e65e6285'}, 'graphics-compiler': {'master': '6bfb47527'}, 'm3d': {'master': 'fad16f82a'}, 'vbios': {'master': '79c044773'}, 'ogl': {'master': '757a3724b'}, \
        # 'd3dtests': {'master': 'a88614bcc'}, 'gr-umd': {'develop': 'da0c850b8', 'release-2.5.0-OEM': '3d2e327ca'}, 'wddm': {'develop': '11ba5447c'}}
 
    umd_rs_list = middle_search('gr-umd',umd_search_list,Pc)
    if not umd_rs_list:
        print("此UMD区间无法确定到问题引入范围")
        # sys.exit(-1)
        kmd_rs_list = middle_search('gr-kmd',kmd_search_list,Pc)
        if not kmd_rs_list:
            print("此KMD区间无法确定到问题引入范围")
            sys.exit(-1)

    umd_fallback(umd_search_list,Pc)


def get_commit_from_deb(deb_rs_list,driver_full_list):
    gr_umd_start_end = []
    gr_kmd_start_end = []
    for deb_info in driver_full_list:
        if deb_info[0] in deb_rs_list:
            rs = subprocess.Popen(f"curl {deb_info[1]}", shell=True, close_fds=True, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE).communicate()
            repo_tag_dict = eval(rs[0].decode())
            gr_umd_start_end.append(repo_tag_dict['gr-umd'][branch])
            gr_kmd_start_end.append(repo_tag_dict['gr-kmd'][branch])
    begin_date = re.search(r"\d{4}.\d{2}.\d{2}",deb_rs_list[0])
    begin_date = begin_date.group()
    end_date = re.search(r"\d{4}.\d{2}.\d{2}",deb_rs_list[1])
    end_date = end_date.group()
    previous_day = datetime.strptime(begin_date,"%Y%m%d") - timedelta(days=1)
    # 设置开始时间为前一天12:00，结束时间为当天的23:00
    previous_day_at_noon = previous_day.replace(hour=12, minute=0, second=0)
    end_date = datetime.strptime(end_date,"%Y%m%d").replace(hour=23,minute=0,second=0)
    # 格式化输出
    commit_begin_date = previous_day_at_noon.strftime("%Y-%m-%d %H:%M:%S")
    commit_end_date = end_date.strftime("%Y-%m-%d %H:%M:%S")
    # print(f"查询开始时间：{commit_begin_date}\n查询结束时间：{commit_end_date}")    
    umd_list = get_commit.get_git_commit_info("gr-umd", branch, commit_begin_date , commit_end_date)
    kmd_list = get_commit.get_git_commit_info("gr-kmd", branch, commit_begin_date , commit_end_date)
    umd_search_list = slice_full_list(gr_umd_start_end,umd_list)
    kmd_search_list = slice_full_list(gr_kmd_start_end,kmd_list)
    print(f"umd_list：{umd_search_list}\nkmd_list：{kmd_search_list}")
    return umd_search_list,kmd_search_list

def deb_fallback(driver_list,Pc):
    deb_rs_list = middle_search('deb',driver_list,Pc)
    return deb_rs_list

def umd_fallback(umd_search_list,Pc):
    umd_rs_list = middle_search('gr-umd',umd_search_list,Pc)
    return umd_rs_list

def kmd_fallback(kmd_search_list,Pc):
    kmd_rs_list = middle_search('gr-kmd',kmd_search_list,Pc)
    return kmd_rs_list

branch = sys.argv[1]
begin_date = sys.argv[2]
end_date = sys.argv[3]
os_type = sys.argv[4] # pc合一包？os单独？
if __name__ == "__main__":
    begin_date = '20240527'
    end_date = '20240529'
    branch = 'develop'
    Test_Host_IP = '192.168.114.8'
    Pc = sshClient(Test_Host_IP,"georgy","dell1234")
    main(branch,begin_date,end_date,Pc)




