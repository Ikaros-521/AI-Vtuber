from bardapi import Bard

"""
访问 https://bard.google.com/
F12 for console 用于控制台的 F12
会话：应用程序→ Cookie → 复制 Cookie 的值 __Secure-1PSID 。
"""
token = ''

bard = Bard(token=token)
content = 'Hello, I am Bard! How can I help you today?'
content = '你好'
audio = bard.speech(content)
with open("speech.ogg", "wb") as f:
  f.write(bytes(audio['audio']))