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
    latest_commits = {}

    for commit in commits:
        commit_time = commit['commit_time']
        # if commit_time not in latest_commits or  commit['commit_time'] in latest_commits:
        latest_commits[commit_time] = commit

    result_commit_ids = [commit['short_id'] for commit in latest_commits.values()]

    return result_commit_ids

if __name__ == "__main__":
    print(get_git_commit_info("gr-umd", "develop", "2024-06-24 12:00:00", "2024-06-25 23:00:00"))


