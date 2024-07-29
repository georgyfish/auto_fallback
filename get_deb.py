#!/usr/bin/python3
import datetime,re,sys
import subprocess
from logManager import logManager
import requests
from bs4 import BeautifulSoup

class deb_info:
    def __init__(self,branch,begin_date,end_date,Pc_info):
        self.log = logManager('get_deb_info')
        self.branch = branch
        self.begin_date = begin_date
        self.end_date = end_date
        self.arch =  Pc_info.arch
        self.glvnd = Pc_info.glvnd
        self.os_type = Pc_info.os_type
        self.architecture = Pc_info.architecture
        self.work_date_list = self.deal(begin_date,end_date)
    
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

    def Check_Driver_URL(self,repo,check_list):
        branch,arch,glvnd,os_type,architecture = (
            self.branch,
            self.arch,
            self.glvnd,
            self.os_type,
            self.architecture
        )
        result = []
        remove_result = [] 
        for commit in check_list:
            file_found = False
            if repo == 'umd':
                url = f"http://oss.mthreads.com/release-ci/gr-umd/{branch}/{commit}_{arch}-mtgpu_linux-xorg-release-hw.tar.gz"
                if glvnd:
                    url = f"http://oss.mthreads.com/release-ci/gr-umd/{branch}/{commit}_{arch}-mtgpu_linux-xorg-release-hw-{glvnd}.tar.gz"
                urls = [url]
            elif repo == 'kmd':
                url = f"http://oss.mthreads.com/sw-build/gr-kmd/{branch}/{commit}/{commit}_{arch}-mtgpu_linux-xorg-release-hw.deb"
                urls = [url]
            else:
                work_date = re.search(r"\d{4}.\d{2}.\d{2}",commit)
                work_date = work_date.group()
                work_date = datetime.datetime.strptime(work_date, "%Y.%m.%d").strftime("%Y%m%d")
                driver_name = f"{commit}+dkms+{glvnd}-{os_type}_{architecture}.deb"
                driver_name_pc = f"{commit}+dkms+{glvnd}-pc_{architecture}.deb"
                url_os_type = f"https://oss.mthreads.com/product-release/{branch}/{work_date}/{driver_name}"
                url_pc = f"https://oss.mthreads.com/product-release/{branch}/{work_date}/{driver_name_pc}"
                urls = [url_pc,url_os_type]
                print(f"{urls=}")
                # # 20240708后使用pc deb测试
                # if work_date.strptime(work_date, "%Y%m%d") > datetime.datetime.strptime("20240708","%Y%m%d"):
                #     driver_name = f"{commit}+dkms+{glvnd}-pc_{architecture}.deb"
                # url = f"https://oss.mthreads.com/product-release/{branch}/{work_date}/{driver_name}"
            for url in urls:
                if self.check_url(url):
                    result.append(commit)
                    file_found = True
                    break
                else:
                    self.log.logger.error(f"URL {url} is not accessible.")
            if not file_found:
                remove_result.append(commit)
        if remove_result:
            self.log.logger.info(f"因oss地址不存在移除{repo}列表{remove_result}")
        return result

    # 通过日期列表、daily_build获取 驱动版本列表
    def get_deb_version_from_date(self):
        result = []
        remove_result = [] 
        daily_build_txts = ['daily_build_pc.txt', 'daily_build.txt']
        # 先尝试获取daily_build_pc.txt，再尝试daily_build.txt
        for work_date in self.work_date_list:
            file_found = False
            # work_date_date = datetime.datetime.strptime(work_date,"%Y%m%d")
            for daily_build_txt in daily_build_txts:
                url = f'https://oss.mthreads.com/product-release/{self.branch}/{work_date}/{daily_build_txt}' 
                try:
                    response = requests.get(url)
                    response.raise_for_status()  # 如果响应不是200，则会抛出异常
                    driver = response.text.splitlines()[0]
                    print(f"成功获取文件：{daily_build_txt}")
                    file_found = True
                    break  # 获取成功则退出循环
                except requests.exceptions.RequestException as e:
                    print(f"未能获取文件：{daily_build_txt}，错误信息：{e}")
            if driver is not None:
                self.log.logger.info(f"{driver=}")
                result.append(driver)
            if not file_found:
                remove_result.append(work_date)
        if remove_result:
            self.log.logger.info(f"因oss daily_build地址不存在移除 {remove_result}")
        result = self.Check_Driver_URL('deb',result)
        return result

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

    # 通过deb_info.txt获取commit信息
    def get_UMD_KMD_commit_from_deb_info(self,deb_list):
        branch = self.branch
        gr_umd_start_end = []
        gr_kmd_start_end = []
        for deb in deb_list:
            deb_date = re.search(r'\d{4}\.\d{2}\.\d{2}',deb).group()
            self.log.logger.info(f"{deb_date=}")
            deb_date = datetime.datetime.strptime(deb_date,"%Y.%m.%d").strftime("%Y%m%d")
            # info.txt 需确认下具体格式
            url = f"https://oss.mthreads.com/porduct-release/{branch}/{deb}_info.txt"
            response = requests.get(url)
            response.raise_for_status()
            tmp_list = response.text.splitlines()
            for tmp in tmp_list:
                key = tmp.split(':')[0]
                value = tmp.split(':')[1]
                if key == 'kmd':
                    kmd_commit = value
                if key == 'umd':
                    umd_commit = value
            gr_umd_start_end.append(umd_commit)
            gr_kmd_start_end.append(kmd_commit)
        self.log.logger.info(f"{gr_umd_start_end=}\n{gr_kmd_start_end=}\n")
        return gr_umd_start_end,gr_kmd_start_end

    # 通过deb日期 repo_tag获取commit信息
    # 两版deb驱动，分别根据repo_tag.txt获取2笔UMD、2笔KMD区间
    # 根据两版deb驱动版本，得到它们的日期，（适用于develop）
    # 根据日期，获取commit列表
    # 截取UMD区间的头尾commit在commit列表中的index序号，切片commit列表
    # 检查每个commit的URL，过滤无法下载的；
    def get_UMD_KMD_commit_from_deb(self,deb_list):
        branch = self.branch
        gr_umd_start_end,gr_kmd_start_end = self.get_UMD_KMD_commit_from_deb_info(deb_list)
        # gr_umd_start_end = []
        # gr_kmd_start_end = []
        # for deb in deb_list:
        #     deb_date = re.search(r'\d{4}\.\d{2}\.\d{2}',deb).group()
        #     self.log.logger.info(f"{deb_date=}")
        #     deb_date = datetime.datetime.strptime(deb_date,"%Y.%m.%d").strftime("%Y%m%d")
        #     url = f"https://oss.mthreads.com/release-ci/repo_tags/{deb_date}.txt"
        #     self.log.logger.info(f"curl {url}")
        #     try:
        #         # response = requests.get(url)
        #         # json_obj = response.json()
        #         # gr_umd_start_end.append(json_obj['gr-umd'][branch])
        #         # gr_kmd_start_end.append(json_obj['gr-kmd'][branch])
        #         rs = subprocess.run(['curl', url], capture_output=True, text=True, check=True)
        #         repo_tag_dict = eval(rs.stdout)
        #         self.log.logger.info(f"{repo_tag_dict=}")
        #         gr_umd_start_end.append(repo_tag_dict['gr-umd'][branch])
        #         gr_kmd_start_end.append(repo_tag_dict['gr-kmd'][branch])
        #     except subprocess.CalledProcessError as e:
        #         self.log.logger.error(f"Error:\n{e.stderr}")
        #     except Exception as e:
        #         self.log.logger.error(f"An unexpected error occurred: \n{e}")
        # self.log.logger.info(f"{gr_umd_start_end=}\n{gr_kmd_start_end=}\n")
        begin_date = re.search(r"\d{4}.\d{2}.\d{2}",deb_list[0]).group()
        end_date = re.search(r"\d{4}.\d{2}.\d{2}",deb_list[1]).group()
        previous_day = datetime.datetime.strptime(begin_date,"%Y.%m.%d") - datetime.timedelta(days=1)
        # 设置开始时间为前一天12:00，结束时间为当天的23:00
        commit_begin_date = previous_day.replace(hour=12, minute=0, second=0).strftime("%Y-%m-%d %H:%M:%S")
        commit_end_date = datetime.datetime.strptime(end_date,"%Y.%m.%d").replace(hour=23,minute=0,second=0).strftime("%Y-%m-%d %H:%M:%S")
        # 格式化输出
        self.log.logger.info(f"commit查询开始时间：{commit_begin_date}\ncommit查询结束时间：{commit_end_date}\n")    
        umd_list = self.get_commits_from_date("gr-umd", commit_begin_date , commit_end_date)
        kmd_list = self.get_commits_from_date("gr-kmd", commit_begin_date , commit_end_date)
        self.log.logger.info(f"{umd_list=}\n{kmd_list=}\n")
        # umd_search_list , kmd_search_list = self.slice_full_list(gr_umd_start_end,umd_list) , self.slice_full_list(gr_kmd_start_end,kmd_list)
        umd_search_list,kmd_search_list = self.Check_Driver_URL("umd",self.slice_full_list(gr_umd_start_end,umd_list)),self.Check_Driver_URL("kmd",self.slice_full_list(gr_kmd_start_end,kmd_list))
        self.log.logger.info(f"{umd_search_list=}\n{kmd_search_list=}\n")
        return umd_search_list,kmd_search_list


    # 通过日期获取commit列表
    def get_commits_from_date(self, repo,begin_time,end_time):
        # branch, begin_time, end_time = (self.branch,self.begin_date,self.end_date)
        branch  = self.branch
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

    # 应该用git获取最好
    # 进入代码目录，
    # branch = f"git branch --contains {commit}" 
    # git log -1 abc123
    # git show {commit}
    def get_commits_from_commit(self,component,commit_list):
        end_date = datetime.datetime.today() + datetime.timedelta(1)
        begin_date = end_date - datetime.timedelta(365)
        end_date = end_date.strftime("%Y-%m-%d %H:%M:%S")
        begin_date = begin_date.strftime("%Y-%m-%d %H:%M:%S")
        if component == 'umd':
            umd_list = self.get_commits_from_date("gr-umd", begin_date , end_date)
            umd_search_list = self.Check_Driver_URL("umd",self.slice_full_list(commit_list,umd_list))
            self.log.logger.info(f"{umd_search_list=}")
            return umd_search_list
        else:
            kmd_list = self.get_commits_from_date("gr-kmd", begin_date , end_date)
            kmd_search_list = self.Check_Driver_URL("kmd",self.slice_full_list(commit_list,kmd_list))
            self.log.logger.info(f"{kmd_search_list=}\n")
            return kmd_search_list

        #     if work_date_date > datetime.datetime.strptime("20240708","%Y%m%d"):
                
        #         for file_name in files_to_try:
        #             url = f'https://oss.mthreads.com/product-release/{self.branch}/{work_date}/{file_name}' 
                    
        #             try:
        #                 # if self.check_url(url)
        #                 response = requests.get(url)
        #                 response.raise_for_status()  # 如果响应不是200，则会抛出异常
        #                 driver = response.text.splitlines()[0]
        #                 self.log.logger.info(f"{driver=}")
        #                 result.append(driver)
        #                 print(f"成功获取文件：{file_name}")
        #                 break  # 获取成功则退出循环
        #             except requests.exceptions.RequestException as e:
        #                 print(f"未能获取文件：{file_name}，错误信息：{e}")
        #         # url = f"https://oss.mthreads.com/product-release/{self.branch}/{work_date}/daily_build_pc.txt"
        #     else:
        #         url = f"https://oss.mthreads.com/product-release/{self.branch}/{work_date}/daily_build.txt"
        #     if self.check_url(url):
        #         self.log.logger.info(f"curl {url}")
        #         try:
        #             rs = subprocess.run(['curl',url], capture_output=True, text=True, check=True)
        #             driver = rs.stdout.splitlines()[0]
        #             self.log.logger.info(f"{driver=}")
        #             result.append(driver)

        #         except subprocess.CalledProcessError as e:
        #         # 打印错误信息
        #             self.log.logger.error(f"Error:\n{e.stderr}")
        #         except Exception as e:
        #         # 处理其他异常
        #             self.log.logger.error(f"An unexpected error occurred: {e}")
        #     else:
        #         self.log.logger.error(f"URL {url} is not accessible.")
        #         remove_result.append(work_date_date)
        #     self.log.logger.info(f"因oss地址不存在移除daily_build {remove_result}")

        #     result = self.Check_Driver_URL(self,'deb',result)
        # return result


if __name__ == '__main__':
    deb_info = deb_info()
    print(deb_info.get_git_commit_info("gr-umd", "develop", "2024-06-24 12:00:00", "2024-06-25 23:00:00"))
    # Pc_info = 
    # deb_list = deb_info('develop','20240701', '20240724',)
    # driver_full_list = deb_list.get_deb_version()
    # print(driver_full_list)
    # 示例 URL
    # url = "https://oss.mthreads.com/product-release/develop/20240625/daily_build.txt"
    # 73ab64766
    # url = "http://oss.mthreads.com/release-ci/gr-umd/develop/73ab64766_x86_64-mtgpu_linux-xorg-release-hw-glvnd.tar.gz"
    # if check_url(url):
    #     print(f"The URL {url} is valid and accessible.")
    # else:
    #     print(f"The URL {url} is not accessible.")
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