#!/usr/bin/python3
import datetime
import subprocess
from logManager import logManager


class deb_info:
    def __init__(self,branch,begin_date,end_date):
        self.log = logManager('get_deb_info')
        self.branch = branch
        self.begin_date = begin_date
        self.end_date = end_date

    @staticmethod
    def deal(begin_date,end_date):
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

    def get_deb_version(self):
        result = []
        work_date_list = self.deal(self.begin_date,self.end_date)
        # self.log = logManager('get_deb_version')
        # error
        for work_date in work_date_list:
            url = f"https://oss.mthreads.com/product-release/{self.branch}/{work_date}/daily_build.txt"
            if self.check_url(url):
                self.log.logger.info(f"curl {url}")
                try:
                    rs = subprocess.run(['curl',url], capture_output=True, text=True, check=True)
                    stdout_list = rs.stdout.splitlines()
                    self.log.logger.info(f"{stdout_list=}")
                    result.append(stdout_list)
                except subprocess.CalledProcessError as e:
                # 打印错误信息
                    self.log.logger.error(f"Error:\n{e.stderr}")
                except Exception as e:
                # 处理其他异常
                    self.log.logger.error(f"An unexpected error occurred: {e}")
            else:
                self.log.logger.error(f"URL {url} is not accessible.")
        return result

    def check_url(self,url):
        try:
            # 使用 curl 命令检查 URL
            # result = subprocess.run(
            #     ['curl', '-Is', url], # 只获取头部信息来快速判断
            #     stdout=subprocess.PIPE,
            #     stderr=subprocess.PIPE
            # )
            result = subprocess.run(
                ['wget', '--spider', '-q', url], # --spider 表示不下载，只检查，-q 表示安静模式
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            # 检查返回码是否为200
            if result.returncode == 0:
                return True
            else:
                return False
        except Exception as e:
            print(f"An error occurred: {e}")
            return False

if __name__ == '__main__':
    deb_list = deb_info('develop','20240624', '20240627')
    driver_full_list = deb_list.get_deb_version()
    print(driver_full_list)
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