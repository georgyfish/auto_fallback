#!/usr/bin/python3
from datetime import datetime, timezone, timedelta
# import middle_search as ms
from get_deb_version import get_deb_version
import subprocess,os,sys,get_commit
import sshClient
from logManager import logManager
import os,sys,time,re

branch = 'develop'
begin_date = '20240620'
end_date = '20240624'
branch = 'develop'
Test_Host_IP = '192.168.114.102'
Host_name = 'swqa'
passwd = 'gfx123456'
Pc = sshClient.sshClient(Test_Host_IP,Host_name,passwd)
if 1000 == Pc.login():
    # test_ssh()
    rs = Pc.execute('uname -m')
    print(f"{rs=}")