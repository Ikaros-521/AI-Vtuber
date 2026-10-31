# pip install volcengine-python-sdk[ark]

from volcenginesdkarkruntime import Ark

client = Ark(
    api_key="408a",
    base_url="https://ark.cn-beijing.volces.com/api/v3",
)

# Non-streaming:
# print("----- standard request -----")
# completion = client.chat.completions.create(
#     model="ep-20240904192312-r4rkc",
#     messages = [
#         {"role": "system", "content": "你是豆包，是由字节跳动开发的 AI 人工智能助手"},
#         {"role": "user", "content": "常见的十字花科植物有哪些？"},
#     ],
# )
# print(completion.choices[0].message.content)

# Streaming:
print("----- streaming request -----")

stream = client.chat.completions.create(
    model="ep-20240904192312-r4rkc",
    messages = [
        {"role": "system", "content": "你是豆包，是由字节跳动开发的 AI 人工智能助手"},
        {"role": "user", "content": "请记住我的问题：1+1=？"},
        {"role": "assistant", "content": "你好！有什么我可以帮忙的吗？"},
        {"role": "user", "content": "我刚才问的什么"},
    ],
    stream=True
)
for chunk in stream:
    if not chunk.choices:
        continue
    print(chunk.choices[0].delta.content, end="")
print()