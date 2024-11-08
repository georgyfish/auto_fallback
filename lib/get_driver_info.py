#!/usr/bin/python3
import datetime,re,sys,os
import requests
from bs4 import BeautifulSoup
import urllib.parse

basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(basedir)
# from lib.logManager import logManager
from lib.oss_tool import OSSTool
from lib.git_lib import GitCommitInfo

class deb_info:
    def __init__(self,branch,begin_date,end_date,pc_info,Log):
        # self.log = logManager('get_deb_info')
        self.log = Log
        self.branch = branch
        self.begin_date = begin_date
        self.end_date = end_date
        self.arch =  pc_info['arch']
        self.glvnd = pc_info['glvnd']
        self.os_type = pc_info['os_type']
        self.architecture = pc_info['architecture']
        self.work_date_list = self.deal(begin_date,end_date)
        self.oss = OSSTool('mtoss', 'mtoss123')
    
    def deal(self,begin_date,end_date):
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


    def daily_build_pc(self,work_date):
        if self.oss.ls('product-release',f'/{self.branch}/{work_date}/daily_build_pc.txt'):
            driver = self.oss.show_text(f'product-release/{self.branch}/{work_date}/daily_build_pc.txt').splitlines()[0]
            driver_name = f"{driver}+dkms+{self.glvnd}-pc_{self.architecture}.deb"
            if self.oss.ls('product-release',f'/{self.branch}/{work_date}/{driver_name}'):
                pc = 'pc'
                return driver,pc
            else:
                return self.no_daily_build(work_date)
        else:
            return self.no_daily_build(work_date)

    def no_daily_build(self,work_date):
        # print(work_date)
        build_ids = []
        files = []
        file_list = self.oss.ls('product-release',f'/{self.branch}/{work_date}/')
        if file_list:
            files = list(map(lambda file:file['name'].split('/')[-1], file_list))
            files = list(filter(lambda file:file.endswith(f'pc_{self.architecture}.deb') and 'server' not in file,files))
            if files:
                pc = 'pc'
            else:
                pc = 'os_type'
                if self.oss.ls('product-release',f'/{self.branch}/{work_date}/daily_build.txt'):
                    driver = self.oss.show_text(f'product-release/{self.branch}/{work_date}/daily_build.txt').splitlines()[0]
                    driver_name = f"{driver}+dkms+{self.glvnd}-{self.os_type}_{self.architecture}.deb"
                    if self.os_type == 'Kylin':
                        driver_name = f"{driver}+dkms-{self.os_type}_{self.architecture}.deb"
                    if self.os_type == 'Ubuntu' and self.architecture != 'amd64':
                        self.log.logger.error(f"oss/product-release/{self.branch}/{work_date}/下不存在支持的驱动")
                        return None
                    elif self.oss.ls('product-release',f'/{self.branch}/{work_date}/{driver_name}'):
                        return driver,pc
                else:
                    files = list(filter(lambda file:file.endswith(f'{self.os_type}_{self.architecture}.deb') and 'server' not in file,files))
            for file in files:
                build_ids.append(file.split('+')[1].split('-')[0])
            # print(build_ids)
            if build_ids:
                driver = list(filter(lambda file:max(build_ids,key=int) in file, files))
                driver = '+'.join(driver[0].split('+')[:2])
                return driver,pc
            else:
                return  None
        else:
            return None

    def get_deb_from_oss(self):
        result = []
        remove_result = [] 
        pc_list = []
        self.log.logger.info(f"查找日期{self.begin_date}-{self.end_date}：")
        for work_date in self.work_date_list:
            rs =  self.daily_build_pc(work_date)
            if  rs :
                driver,pc = rs
                pc_list.append(pc)
                # self.log.logger.info(f"{driver=}")
                result.append(driver)
            else:
                remove_result.append(work_date)
        if remove_result:
            self.log.logger.info(f"因oss地址下不存在文件移除 {remove_result}")          
        # self.log.logger.info(f"\n{result=}\n{len(result)=}")
        # self.log.logger.info(f"\n{pc_list=}\n{len(pc_list)=}")
        if len(result) == len(pc_list):
            return result,pc_list

    # 检查url 响应状态码是否是200
    def check_url(self,url):
        try:
            responce = requests.get(url)
            if responce.status_code == 200:
                return True
            else:
                return False
        except Exception as e:
            print(f"An error occurred: {e}")
            return False


    def slice_full_list(self,start_end_list, full_list):
        try:
            if start_end_list[0] in full_list:
                index_start = full_list.index(start_end_list[0])
            else:
                self.log.logger.error("input error!")
                sys.exit(-1)
            if start_end_list[1] in full_list:
                index_end = full_list.index(start_end_list[1])
            else:
                self.log.logger.error("input error!")
                sys.exit(-1)        
            return full_list[index_start:index_end+1]
        except IndexError:
            self.log.logger.error(f"list index out of range! {start_end_list} not in {full_list}")
            sys.exit(-1)

    @staticmethod
    def url_encode(string):
        # 使用 quote 方法进行 URL 编码
        encoded_string = urllib.parse.quote(string, safe='')
        return encoded_string

    # deb_info commit信息，并转化为字典存储
    def get_deb_info(self,deb_version):
        branch = self.branch
        deb_date = re.search(r'\d{4}\.\d{2}\.\d{2}',deb_version).group()
        deb_date = datetime.datetime.strptime(deb_date,"%Y.%m.%d").strftime("%Y%m%d")
        deb_version = deb_info.url_encode(deb_version)
        url = f"https://oss.mthreads.com/product-release/{branch}/{deb_date}/{deb_version}_info.txt"
        response = requests.get(url)
        response.raise_for_status()
        commit_list = response.text.splitlines()
        result = {}
        for commit in commit_list:
            key = commit.split(':')[0]
            value = commit.split(':')[1].lstrip()
            result[key] = value
        self.log.logger.info(f"{deb_date=}\ndeb_info={result}\t")
        return result    

    # 通过deb_list获取UMD/KMD commit_List信息
    def get_commit_from_debinfo(self,component,deb_list):
        commitList = []
        for deb_version in deb_list:
            rs = self.get_deb_info(deb_version)
            commit = rs[component]
            commitList.append(commit)
        self.log.logger.info(f"\n{component} commit list ={commitList}")
        return commitList

    # 通过git获取commits列表
    def get_commits_from_deb_list(self,component,deb_list):
        # 包含两个commit,头尾的列表
        component_commitList = self.get_commit_from_debinfo(component,deb_list) 
        Git = GitCommitInfo()
        Git.update()
        Commit_list = self.Check_Driver_URL(component,Git.get_commits(f"gr-{component}",self.branch, component_commitList))
        return Commit_list
        # umd_search_list = self.Check_Driver_URL('umd',o.get_commits('gr-umd',self.branch, gr_umd_start_end))
        # kmd_search_list = self.Check_Driver_URL('kmd',o.get_commits('gr-kmd',self.branch, gr_kmd_start_end))
        # return umd_search_list,kmd_search_list

    #从输入的commit，得到回退列表
    def get_commits_from_commit(self,component,commit_list):
        Git = GitCommitInfo()
        Git.update()
        Commit_list = self.Check_Driver_URL(component,Git.get_commits(f"gr-{component}",self.branch, commit_list))
        return Commit_list

    # # 通过deb_info.txt获取commit信息
    # def get_UMD_KMD_commit_from_deb_info(self,deb_list):
    #     gr_umd_start_end = []
    #     gr_kmd_start_end = []
    #     for deb_version in deb_list:
    #         rs = self.get_deb_info(deb_version)
    #         umd_commit,kmd_commit = rs['umd'],rs['kmd']
    #         gr_umd_start_end.append(umd_commit)
    #         gr_kmd_start_end.append(kmd_commit)
    #     self.log.logger.info(f"\n{gr_umd_start_end=}\n{gr_kmd_start_end=}")
    #     return gr_umd_start_end,gr_kmd_start_end

    # 通过repo_tag.txt获取commit信息
    def get_commit_from_repo_tag_txt(self,deb_version):
        branch = self.branch
        deb_date = re.search(r'\d{4}\.\d{2}\.\d{2}',deb_version).group()
        self.log.logger.info(f"{deb_date=}")
        deb_date = datetime.datetime.strptime(deb_date,"%Y.%m.%d").strftime("%Y%m%d")
        url = f"https://oss.mthreads.com/release-ci/repo_tags/{deb_date}.txt"
        try:
            response = requests.get(url)
            json_obj = response.json()
            umd_commit = json_obj['gr-umd'][branch]
            kmd_commit = json_obj['gr-kmd'][branch]
        except Exception as e:
            self.log.logger.error(f"An unexpected error occurred: \n{e}")
        return umd_commit,kmd_commit


    
    # """
    # 通过deb日期 repo_tag获取commit信息
    # 两版deb驱动，分别根据repo_tag.txt获取2笔UMD、2笔KMD区间
    # 根据两版deb驱动版本，得到它们的日期，（适用于develop）
    # 根据日期，获取commit列表
    # 截取UMD区间的头尾commit在commit列表中的index序号，切片commit列表
    # 检查每个commit的URL，过滤无法下载的；
    # """
        # begin_date = re.search(r"\d{4}.\d{2}.\d{2}",deb_list[0]).group()
        # end_date = re.search(r"\d{4}.\d{2}.\d{2}",deb_list[1]).group()
        # previous_day = datetime.datetime.strptime(begin_date,"%Y.%m.%d") - datetime.timedelta(days=1)
        # # 设置开始时间为前一天12:00，结束时间为当天的23:00
        # commit_begin_date = previous_day.replace(hour=12, minute=0, second=0).strftime("%Y-%m-%d %H:%M:%S")
        # commit_end_date = datetime.datetime.strptime(end_date,"%Y.%m.%d").replace(hour=23,minute=0,second=0).strftime("%Y-%m-%d %H:%M:%S")
        # # 格式化输出
        # self.log.logger.info(f"commit查询开始时间：{commit_begin_date}\ncommit查询结束时间：{commit_end_date}\n")    
        # umd_list = self.get_commits_from_date("gr-umd", commit_begin_date , commit_end_date)
        # kmd_list = self.get_commits_from_date("gr-kmd", commit_begin_date , commit_end_date)
        # self.log.logger.info(f"{umd_list=}\n{kmd_list=}\n")
        # # umd_search_list , kmd_search_list = self.slice_full_list(gr_umd_start_end,umd_list) , self.slice_full_list(gr_kmd_start_end,kmd_list)
        # umd_search_list,kmd_search_list = self.Check_Driver_URL("umd",self.slice_full_list(gr_umd_start_end,umd_list)),self.Check_Driver_URL("kmd",self.slice_full_list(gr_kmd_start_end,kmd_list))
        # self.log.logger.info(f"{umd_search_list=}\n{kmd_search_list=}\n")
        # return umd_search_list,kmd_search_list


    # 通过日期获取commit列表
    def get_commits_from_date(self, repo,begin_time,end_time):
        # branch, begin_time, end_time = (self.branch,self.begin_date,self.end_date)
        branch  = self.branch
        commits = []
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
        commits = [commit['short_id'] for commit in latest_commits.values()]
        return commits

    # 通过日期列表、daily_build获取 驱动版本列表
    def get_deb_version_from_date(self):
        result = []
        remove_result = [] 
        pc_list = []
        daily_build_txts = ['daily_build_pc.txt', 'daily_build.txt']
        # 先尝试获取daily_build_pc.txt，再尝试daily_build.txt
        for work_date in self.work_date_list:
            file_found = False
            pc = None
            driver = None
            for daily_build_txt in daily_build_txts:
                url = f'https://oss.mthreads.com/product-release/{self.branch}/{work_date}/{daily_build_txt}' 
                try:
                    response = requests.get(url)
                    response.raise_for_status()  # 如果响应不是200，则会抛出异常
                    driver = response.text.splitlines()[0]
                    self.log.logger.info(f"成功获取文件：{daily_build_txt}")
                    # 如果是pc的包，添加pc标签
                    if daily_build_txt == 'daily_build_pc.txt':
                        pc = 'pc'
                    else:
                        pc = 'os_type'
                    file_found = True
                    break  # 获取成功则退出循环
                except requests.exceptions.RequestException as e:
                    self.log.logger.error(f"未能获取文件：{daily_build_txt}，错误信息：{e}")
            if pc:
                pc_list.append(pc)
            if driver is not None:
                self.log.logger.info(f"{driver=}")
                result.append(driver)
            if not file_found:
                remove_result.append(work_date)
        if remove_result:
            self.log.logger.info(f"因oss daily_build地址不存在移除 {remove_result}")
        result = self.Check_Driver_URL('deb',result,pc_list)
        return result,pc_list

        
    #     end_date = datetime.datetime.today() + datetime.timedelta(1)
    #     begin_date = end_date - datetime.timedelta(365)
    #     end_date = end_date.strftime("%Y-%m-%d %H:%M:%S")
    #     begin_date = begin_date.strftime("%Y-%m-%d %H:%M:%S")
    #     if component == 'umd':
    #         umd_list = self.get_commits_from_date("gr-umd", begin_date , end_date)
    #         umd_search_list = self.Check_Driver_URL("umd",self.slice_full_list(commit_list,umd_list))
    #         self.log.logger.info(f"{umd_search_list=}")
    #         return umd_search_list
    #     else:
    #         kmd_list = self.get_commits_from_date("gr-kmd", begin_date , end_date)
    #         kmd_search_list = self.Check_Driver_URL("kmd",self.slice_full_list(commit_list,kmd_list))
    #         self.log.logger.info(f"{kmd_search_list=}\n")
    #         return kmd_search_list
    
    def Check_Driver_URL(self,repo,check_list,pc_list=None):
        branch,arch,glvnd,os_type,architecture = (
            self.branch,
            self.arch,
            self.glvnd,
            self.os_type,
            self.architecture
        )
        o = OSSTool('mtoss', 'mtoss123')
        result = []
        remove_result = [] 
        for commit in check_list:
            file_found = False
            if repo == 'umd':
                bucket = 'release-ci'
                path = f'/gr-umd/{branch}/{commit}_{arch}-mtgpu_linux-xorg-release-hw-{glvnd}.tar.gz'
                if not glvnd:
                    path = f'/gr-umd/{branch}/{commit}_{arch}-mtgpu_linux-xorg-release-hw.tar.gz'
            elif repo == 'kmd':
                bucket = 'sw-build'
                path = f'/gr-kmd/{branch}/{commit}/{commit}_{arch}-mtgpu_linux-xorg-release-hw.deb'
            else:
                # pc包和非pc包
                bucket = 'product-release'
                driver_name = f"{commit}+dkms+{glvnd}-{os_type}_{architecture}.deb"
                if pc_list:
                    pc = pc_list[check_list.index(commit)]
                    if pc == 'pc':
                        driver_name = f"{commit}+dkms+{glvnd}-{pc}_{architecture}.deb"
                    else:
                        if os_type == 'Kylin':
                            driver_name = f"{commit}+dkms-{os_type}_{architecture}.deb"
                work_date = re.search(r"\d{4}.\d{2}.\d{2}",commit)
                work_date = work_date.group()
                work_date = datetime.datetime.strptime(work_date, "%Y.%m.%d").strftime("%Y%m%d")
                path = f'/{branch}/{work_date}/{driver_name}'
            if o.ls(bucket, path):
                result.append(commit)
                file_found = True
            else:
                self.log.logger.error(f"URL {bucket}{path} is not accessible.")
            if not file_found:
                remove_result.append(commit)
        if remove_result:
            self.log.logger.info(f"因oss地址不存在移除{repo}列表{remove_result}")
        return result
        
    # 增加一个需求，根据short_id去找到 完整commitID
    def get_commitID_from_shortID(short_id):
        pass


if __name__ == '__main__':
    pass
    # import sshClient,logManager
    # pc_info = sshClient.sshClient("192.168.114.55","swqa","gfx123456").info
    # log = logManager('192.168.114.12')
    # deb_info_obj = deb_info('develop','20240801', '20240808',pc_info,log)
    # deb_info_obj.get_deb_from_oss()
    # import yq.auto_fallback.lib.sshClient as sshClient
    # pc_info = sshClient.sshClient("192.168.114.55","swqa","gfx123456").info
    # deb_info = deb_info("develop", "20240711", "20240712",pc_info)
    # # print(deb_info.get_git_commit_info("gr-umd", "develop", "2024-06-24 12:00:00", "2024-06-25 23:00:00"))
    # rs = deb_info.get_deb_version_from_date()
    # print(rs)