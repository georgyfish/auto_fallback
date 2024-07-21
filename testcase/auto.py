#!/usr/bin/python3

"""
regexp="socinext|cdns|trilinear|fail|error|timeout|underrun|phy err on"
echo $regexp
except_reg="local error reg"
if [[ $1 == all ]];then
    sudo dmesg -c -T|grep -i -E "$regexp"|grep -v "$except_reg"
else
    sudo dmesg -c -T|grep -i -E "mtgpu|mtsnd|MUSA|PVR"|grep -i -E "$regexp"|grep -v "$except_reg"
fi

"""

def dmesg(Pc):
    regexp="socinext|cdns|trilinear|fail|error|timeout|underrun|phy err on"
    except_reg="local error reg"
    cmd = f"sudo dmesg -c -T|grep -i -E \"mtgpu|mtsnd|MUSA|PVR\"|grep -i -E {regexp}|grep -v {except_reg}"
    rs = Pc.execute(cmd)[0]
    return rs


# """
# glmark2\glxgears\
# unixbench score
# heaven/valley
# manhattan  gles
# webgl
# fullscreen 

# """
def perf(Pc,app,fullscreen=""):
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
    return rs