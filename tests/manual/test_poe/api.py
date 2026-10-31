import poe
import json

token = ''
proxy = 'http://127.0.0.1:10811'
# proxy = None

client = poe.Client(token=token, proxy=proxy)

print(json.dumps(client.bot_names, indent=2))