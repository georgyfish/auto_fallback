#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os,requests
from minio import Minio
from bs4 import BeautifulSoup
from minio.error import S3Error
# from comm.logManager import logManager

class minio():
    def __init__(self):
        self.client = Minio( "oss.mthreads.com", access_key="mtoss", secret_key="mtoss123")
        # self.log = logManager("minio")

    def list(self, bucket, prefix):
        """
        list all file which is in the path `bucket/prefix/`
        """
        list = []
        try:
            file_list = self.client.list_objects(bucket_name=bucket, prefix=prefix, recursive=True)
            for obj in file_list:
                file = {
                    "file_path" : os.path.join(obj.bucket_name, prefix), 
                    "file_name" : obj.object_name.split('/')[-1], 
                    "file_size" : obj.size, 
                    "last_modified" : obj.last_modified,
                    "content_type" : obj.content_type
                }
                list.append(file)
        except S3Error as e:
            # print("[error]:", e)
            # self.log.logger.warning(e)
            pass
        return list

    def show(self, bucket: str, object: str):
        """
        show the `object`'s(file) content which is in `bucket`
        """
        try:
            data = self.client.get_object(bucket, object)
            # Read data from response.
            return data.data.decode("utf-8")
        finally:
            data.close()
            data.release_conn()

    def download(self, bucket, object, filename):
        """
        download file from minio
        """
        try:
            self.client.fget_object(bucket, object, filename)
            return 0
        except S3Error as e:
            print(f"[Error] {e}")
            return 1

    def upload(self, bucket, objiect, filename):
        """
        upload local file to minio
        """
        try:
            self.client.fput_object(bucket,objiect,filename)
        except S3Error as e:
            print(f"[Error] {e}")
            return 1

def getCommit(repo, branch, begin_time, end_time):
    """
    通过爬取http://192.168.114.118/td/code_commit/list的内容获取commit信息
    
    :param repo: 代码仓库
    :param branch: 代码分支
    :param begin_time: 开始时间，从begin_time开始获取commit信息
    :param end_time: 结束时间，获取end_time之前的commit信息
    :return: :class:`list` object
    """
    results = []
    data = {
        # http://192.168.114.118/td/code_commit/list
        "repo" : repo,
        "branch" : branch,
        "begin_time" : begin_time,
        "end_time" : end_time
    }
    html = requests.get("http://192.168.114.118/td/code_commit/list", params=data)
    soup = BeautifulSoup(html.text, "html.parser")
    # print(soup.prettify())  #打印soup对象的内容，格式化输出
    for tr in soup.select('tbody tr'):
        commit = {}
        for td in tr.select('td'):
            commit[td['name']] = td.get_text()
        results.insert(0, commit)
    return results


if __name__ == "__main__":
    myminio = minio()
    # print(myminio.list("product-release", "/develop/20240101/"))
    myminio.upload('tmp', '/junhui.yan/uos+x300.txt', "/home/swqa/uos+x300.txt")
    # print(myminio.show("product-release", "/test-dawei/20240308/musa_2024.03.08-release-2.5.0+9795_info.txt"))
    # myminio.download("product-release", "/test-dawei/20240308/musa_2024.03.08-release-2.5.0+9795_info.txt", "./musa_2024.03.08-release-2.5.0+9795_info.txt")

    # print(getCommit("gr-kmd", "develop", "2024-02-29 00:00:00", "2024-03-01 00:00:00"))

