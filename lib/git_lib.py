import subprocess
import os
from datetime import datetime

class GitCommitInfo():
    def __init__(self):
        self.commit_info = {
            'gr-kmd':{
                'develop':[],
                'release-2.1.0':[],
                'release-2.5.0':[],
                'release-2.5.0-OEM':[]
            },
            'gr-umd':{
                'develop':[],
                'release-2.1.0':[],
                'release-2.5.0':[],
                'release-2.5.0-OEM':[]
            }
        }

    def get_git_commit_info(self, repo, branch):
        result = []
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..','app','db','code', repo)
        cmd = f"cd {path};git checkout {branch};git branch -u origin/{branch} {branch};git fetch"
        rs = subprocess.Popen(cmd, shell=True, close_fds=True, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE, preexec_fn = os.setsid, encoding="utf-8")
        rs.communicate(timeout=30)
        cmd = f"cd {path};git log origin/{branch} --oneline --date=format:'%Y-%m-%d %H:%M:%S' --pretty=format:'%H***%cd***%s***%ae'"
        rs = subprocess.Popen(cmd, shell=True, close_fds=True, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE, preexec_fn = os.setsid, encoding="utf-8")
        for line in rs.stdout.readlines():
            commit_id,time_str,commit_msg,author_email = line.split("***")
            time_o = datetime.strptime(time_str,'%Y-%m-%d %H:%M:%S')
            result.append([commit_id, time_o,commit_msg,author_email])
        return result

    def update(self):
        for repo,branchs in self.commit_info.items():
            for branch,_ in branchs.items():
                try:
                    self.commit_info[repo][branch] = self.get_git_commit_info(repo, branch)
                except Exception as e:
                    print(e)

    def get_submit_time(self, repo, branch, commit_id):
        result = self.commit_info.get(repo)
        if result:
            result = result.get(branch)
        if result:
            result = list(filter(lambda arr:arr[0][:9] == commit_id, result))
            submit_time = result[0][1].strftime('%Y-%m-%d %H:%M:%S')
        return submit_time

    def get(self, repo, branch, start_time, end_time):
        result = self.commit_info.get(repo)
        if result:
            result = result.get(branch)
        if result:
            start_time_o = datetime.strptime(start_time,'%Y-%m-%d %H:%M:%S') 
            end_time_o = datetime.strptime(end_time,'%Y-%m-%d %H:%M:%S')
            result = list(filter(lambda arr:arr[1] >=start_time_o and arr[1] <= end_time_o, result))
        return result

    def get_commits(self, repo, branch,  commit_list):
        start = commit_list[0]
        end = commit_list[-1]
        start_time = self.get_submit_time(repo,branch,start)
        end_time = self.get_submit_time(repo, branch, end)
        result = self.get(repo, branch, start_time, end_time)
        return result

if __name__ == '__main__':
    o = GitCommitInfo()
    o.update()
    # print(o.commit_info)
    print(o.get('gr-umd','develop','2024-07-22 00:00:00','2024-07-24 23:20:35'))
    # print(o.get('gr-umd','release-2.5.0','2023-10-12 14:20:35','2023-10-22 14:20:35'))
    # print(o.get_submit_time('gr-umd', 'develop', 'bae16c398'))
    #print(o.get('gr-umd','develop','2023-04-17 14:20:35','2023-04-22 14:20:35'))
