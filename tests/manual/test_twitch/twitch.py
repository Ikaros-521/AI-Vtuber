import socks, re
from emoji import demojize

server = 'irc.chat.twitch.tv'
port = 6667
nickname = '主人'
token = 'oauth:xxx' # 访问 https://twitchapps.com/tmi/ 获取
user = 'love_ikaros' # 你的Twitch用户名 Your Twitch username
channel = '#prettyyjj' # 要从中检索消息的频道，注意#必须携带在头部 The channel you want to retrieve messages from

# 代理服务器的地址和端口
proxy_server = "127.0.0.1"
proxy_port = 10809

# 配置代理服务器
socks.set_default_proxy(socks.HTTP, proxy_server, proxy_port)

# 创建socket对象
sock = socks.socksocket()

try:
    sock.connect((server, port))
    print("成功连接 Twitch IRC server")
except Exception as e:
    print(f"连接 Twitch IRC server 失败: {e}")


sock.send(f"PASS {token}\n".encode('utf-8'))
sock.send(f"NICK {nickname}\n".encode('utf-8'))
sock.send(f"JOIN {channel}\n".encode('utf-8'))

regex = r":(\w+)!\w+@\w+\.tmi\.twitch\.tv PRIVMSG #\w+ :(.+)"

while True:
    try:
        resp = sock.recv(2048).decode('utf-8')

        # 输出所有接收到的内容，包括PING/PONG
        # print(resp)

        if resp.startswith('PING'):
                sock.send("PONG\n".encode('utf-8'))

        elif not user in resp:
            resp = demojize(resp)
            match = re.match(regex, resp)

            username = match.group(1)
            message = match.group(2)
            
            
            chat = '[' + username + ']: ' + message
            print(chat)

    except Exception as e:
        print("Error receiving chat: {0}".format(e))