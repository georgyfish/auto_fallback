#!/usr/bin/env python3
#import requests
import urllib.request
import json
import base64
import os
#import shutil
import ssl

class OSSTool:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        ssl._create_default_https_context = ssl._create_unverified_context
        self.login()

    def login(self):
        url = "https://oss.mthreads.com:9001/api/v1/login"
        payload = json.dumps({
            "accessKey": self.username,
            "secretKey": self.password,
        })
        headers = {
            'Content-Type': 'application/json',
        }
        #response = requests.request("POST", url, headers=headers, data=payload).text
        data = bytes(payload, encoding='utf8')
        request = urllib.request.Request(url=url, data=data, headers=headers, method='POST')
        response = urllib.request.urlopen(request).read().decode('utf-8')
        try:
            self.token = json.loads(response)["sessionId"]
        except Exception:
            raise Exception("login faild")
    
    def gen_headers(self):
        return {
            'Content-Type': 'application/json',
            'Cookie': f"token={self.token}",
        }

    def get_buckets(self):
        url = "https://oss.mthreads.com:9001/api/v1/buckets"
        headers = self.gen_headers()
        request = urllib.request.Request(url=url, headers=headers, method='GET')
        response = urllib.request.urlopen(request).read().decode('utf-8')
        return json.loads(response)

    def ls(self, bucket, path):
        rs = []
        prefix = OSSTool.make_prefix(path)
        url = f"https://oss.mthreads.com:9001/api/v1/buckets/{bucket}/objects?prefix={prefix}"
        headers = self.gen_headers()
        #response = requests.request("GET", url, headers=headers).text
        request = urllib.request.Request(url=url, headers=headers, method='GET')
        response = urllib.request.urlopen(request).read().decode('utf-8')
        return json.loads(response)["objects"]

    def download(self, path, local_path = None):
        print(f"开始下载文件：{path}")
        url = f"https://oss.mthreads.com/{path}"
        request = urllib.request.Request(url=url, method='GET')
        response = urllib.request.urlopen(request).read()#.decode('utf-8')
        print(f"结束下载文件：{path}")
        if local_path:
            with open(local_path, "wb") as f:
                f.write(response)
        return response

    def show_text(self,path):
        url = f"https://oss.mthreads.com/{path}"
        request = urllib.request.Request(url=url, method='GET')
        response_text = urllib.request.urlopen(request).read().decode('utf-8')
        # print(response_text)
        return response_text
        

    #TO DO
    def upload(self, path):
        pass
        #print(f"开始上传文件：{path}")
        #url = f'https://oss.mthreads.com:9001/api/v1/buckets/product-release/objects/upload?prefix={prefix}'
        #request = urllib.request.Request(url=url, headers={'Content-Type':'multipart/form-data'}, method='POST')
        #response = urllib.request.urlopen(request).read()#.decode('utf-8')
        #print(f"结束上传文件：{path}")
        #return response

    @staticmethod
    def make_prefix(s):
        return base64.b64encode(s.encode()).decode()
    
    @staticmethod
    def decode_prefix(s):
        return base64.b64decode(s)
    


        

if __name__ == "__main__":
    o = OSSTool('mtoss', 'mtoss123')
    # print(o.ls('release-ci', '/gr-umd/release-kylin-desktop-v1.0/dkms-deb/'))
    s =  o.ls('product-release', '/develop/20240301/')
    print(f"{type(s)=}\n{s=}")
    print(o.show_text('product-release/release-2.5.0/20240308/musa_2024.03.08-2.5.0+9793_info.txt'))
    # rs = o.download('/product-release/ddk_release/Kylin_integration/Kylin2209_integration_1.0.29/musa_1.0.29-kylin_version_info.txt')
    # rs = o.download('/product-release/develop/20230209/musa_2023.02.09-D2757Ubuntu_amd64-pstate.deb')
    # print(rs.decode())
