import bardapi

"""
访问 https://bard.google.com/
F12 for console 用于控制台的 F12
会话：应用程序→ Cookie → 复制 Cookie 的值 __Secure-1PSID 。
"""
token = ''
proxies = {
    'http': 'http://127.0.0.1:10809',
    'https': 'http://127.0.0.1:10809'
}
#proxies = None

input_text = "你好"
response = bardapi.core.Bard(token, proxies=proxies, timeout=30).get_answer(input_text)
print(response)
print(response["content"])
# bard = Bard(token=token, proxies=proxies, timeout=30)
# bard.get_answer("你好")['content']