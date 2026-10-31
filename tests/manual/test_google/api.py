from pygtrans import Translate

client = Translate(proxies={'https': 'http://localhost:10809'})

text = client.detect('Answer the question.')
print(text)

# 检测语言
text = client.detect('Answer the question.')
print(text)

# 翻译句子
text = client.translate('你好', target='en', source='zh-CN')
print(text)

# 文本到语音
tts = client.tts('こにちわ', target='ja')
open('こにちわ.wav', 'wb').write(tts)