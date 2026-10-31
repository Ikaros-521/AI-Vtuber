# 1. 导入 WinBotMain 类
from PyAibote import WinBotMain
import time,os

# 2. 自定义一个脚本类，继承 WinBotMain
class CustomWinScript(WinBotMain):

    # 2.1. 设置是否终端打印输出 DEBUG：输出， INFO：不输出, 默认打印输出
    Log_Level = "DEBUG" 

    # 2.2. 终端打印信息是否存储LOG文件 True： 储存， False：不存储
    Log_Storage = True  


    # 2.3. 注意：script_main 此方法是脚本执行入口必须存在此方法
    def script_main(self):
        # 查询所有窗口句柄
        # result = self.find_windows()
        # print(result)
        print("开始执行自定义脚本")
    
        # 使用示例 [Demo]
        result = self.init_speech_clone_service("178asdf325c95eafdaaasee3bbf64741", "tIdj8l8nPdqV86Ueasdf")
        print(result)

        # 使用示例 [Demo]
        result = self.init_metahuman("F:/AiboteHumanLive/DigitalHumanMain_V1.0.4_RC/Static/humanModelFemale", 0.5, 0.5, False)
        print(result)

        # result = self.train_human_model(
        #     "dfjklDJFLJlfjkdljf", 
        #     "E:\\GitHub_pro\\AI-Vtuber\\tests\\test_aibote\\1.png", 
        #     "E:\\GitHub_pro\\AI-Vtuber\\tests\\test_aibote\\humanModel", 
        #     "E:\\GitHub_pro\\AI-Vtuber\\tests\\test_aibote\\newHumanModel"
        # )
        # print(result)

        result = self.metahuman_speech("D:/AiboteMetahuman/voice/1.mp3", "PyAibote is an excellent automation framework", "zh-cn", "zh-cn-XiaochenNeural", 0, True, 0, "General")


if __name__ == '__main__':
    # 3. IP为:0.0.0.0, 监听 9999 号端口
    # 3.1. 在远端部署脚本时，请设置 Debug=False，客户端手动启动 WindowsDriver.exe 时需指定远端 IP 或端口号
    # 3.2. 命令行启动示例："127.0.0.1" 9999 {'Name':'PyAibote'}
    CustomWinScript.execute("0.0.0.0", 9999, Debug=True)