#!/usr/bin/python3
from datetime import datetime, timezone, timedelta
# import middle_search as ms
from get_deb_version import get_deb_version
import subprocess,os,sys,get_commit
import sshClient
from logManager import logManager
import os,sys,time,re
import test

def test_dmesg(Pc,regexp):
    rs = Pc.execute(f"dmesg |grep -iE 'mtgpu|mtsnd|MUSA|PVR'| \
        grep -iE {regexp} |grep -v 'local error reg'")
    Output = rs[0]
    if not Output:
        return True
    else:
        return False

def test_perf(benchmark,Target_score):
    rs = Pc.execute(f"/home/{exec_user}/xc_tool/testcase/xc_run_{benchmark}.sh ")
    if not rs[0]:
        score = rs[0].split('测试结果:')[-1]
        if (Target_score - score)/Target_score*100 >= 5:
            print(f"{benchmark}测试结果{score} less than {Target_score} 5%")
            return False
        else:
            return True
            
branch = 'develop'
begin_date = '20240620'
end_date = '20240624'
branch = 'develop'
Test_Host_IP = '192.168.114.102'
Host_name = 'swqa'
passwd = 'gfx123456'
Pc = sshClient.sshClient(Test_Host_IP,Host_name,passwd)
if 1000 == Pc.login():
    rs = test.get_Pc_info(Pc)
    print(f"{rs=}")
    glvnd, os_type, arch, architecture, dm_type, kernel_version, exec_user = (
        rs['glvnd'], 
        rs['os_type'], 
        rs['arch'], 
        rs['architecture'], 
        rs['dm_type'], 
        rs['kernel_version'], 
        rs['exec_user']
    )