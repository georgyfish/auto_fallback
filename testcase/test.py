#!/usr/bin/python3
# 补充测试用例

def test_dmesg(Pc):
    regexp="socinext|cdns|trilinear|fail|error|timeout|underrun|phy err on"
    except_reg="local error reg|mtgpu: module verification failed:|Server Errors: 0|MUSA Errors: WGP:0, TRP:0|MULTICORE_AXI_ERROR|pvr_component_ops|gpu device suspend enter|gpu device suspend exit|gpu device resume enter|gpu device resume exit|signature and/or required key missing|Clear aer status and root error status"
    except_reg="local error reg"
    cmd = f"sudo dmesg  -T|grep -i -E \"mtgpu|mtsnd|MUSA|PVR\"|grep -i -E {regexp}|grep -v {except_reg}"
    rs = Pc.execute(cmd)[0]
    if rs:
        return False
    else:
        return True


# """
# glmark2\glxgears\
# unixbench score
# heaven/valley
# manhattan  gles
# webgl
# fullscreen 

# """
def test_perf(Pc,app,target_score,fullscreen=""):
    valid_app_list = ["glmark2","glxgears","unixbench-2D","unixbench-multicore","heaven","valley","manhattan"]
    if app in valid_app_list:   
        if app == "glmark2" or app == "glxgears":
            if fullscreen == "*fullscreen":
                cmd = f"/home/swqa/xc_tool/testcase/xc_run_{app}.sh --fullscreen"
        else:
            cmd = f"/home/swqa/xc_tool/testcase/xc_run_{app}.sh "
    else:
        print(f"Only suppport {valid_app_list}")
    lines = Pc.execute(cmd)[0]
    for line in lines:
        if "测试结果" in line:
            rs = line.split(":")[-1]
    if rs:
        if rs == target_score:
            return True
    return False

class Test:
    def __init__(self,case) -> None:
        self.case = case

    def test(self):
        testcases = ['dmesg','perf']
        if self.case in testcases:
            # auto test
            # test_{self.case}
            pass
        else:
            # manual test
            rs = input("请手动测试后输入测试结果：pass/fail\n")
            return rs