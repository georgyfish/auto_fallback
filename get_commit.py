#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup

def get_git_commit_info(repo, branch, begin_time, end_time):
    commits = []
    commit_list = []
    latest_commits = {}
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
        commits.insert(0, commit)
    # for commit in commits:
    #     # UMD list 修改， 因为umd可能有重复的commit，两笔commit可能是同一笔，当是同一笔commit时，只有最后一笔才有umd tar包； 
    #     # 如果相邻两笔commit merge时间相同，则只取后一笔

    #     commit_time = commit['commit_time']
    #     commit_id = commit['commit_id']
    #     if commit_time not in latest_commits or  latest_commits[commit_time]['commit_id'] < commit['commit_id']:
    #         latest_commits[commit_time] = commit
    # commit_list = [commit['short_id'] for commit in latest_commits.values()]
    latest_commits = {}

    for commit in commits:
        commit_time = commit['commit_time']
        # if commit_time not in latest_commits or  commit['commit_time'] in latest_commits:
        latest_commits[commit_time] = commit

    result_commit_ids = [commit['short_id'] for commit in latest_commits.values()]

    return result_commit_ids

if __name__ == "__main__":
    print(get_git_commit_info("gr-umd", "develop", "2024-05-27 12:00:00", "2024-05-29 23:00:00"))


