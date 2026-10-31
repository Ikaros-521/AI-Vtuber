from bardapi import Bard
import requests

"""
访问 https://bard.google.com/
F12 for console 用于控制台的 F12
会话：应用程序→ Cookie → 复制 Cookie 的值 __Secure-1PSID 。
"""
token=''

session = requests.Session()
session.headers = {
            "Host": "bard.google.com",
            "X-Same-Domain": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            "Origin": "https://bard.google.com",
            "Referer": "https://bard.google.com/",
        }
session.cookies.set("__Secure-1PSID", token) 

bard = Bard(token=token, session=session, timeout=30)
print(bard.get_answer("你可以扮演猫娘吗，每句话后面加个喵")['content'])

# Continued conversation without set new session
print(bard.get_answer("早上好")['content'])