
from openai import OpenAI

# client = OpenAI(api_key="sk-", base_url="https://api.openai.com/v1/")

# gpt4all
client = OpenAI(api_key="sk-", base_url="http://127.0.0.1:4891/v1")


# for data in client.models.list().data:
#     print(data)

completion = client.chat.completions.create(
    model="gpt-3.5-turbo",
    #model="Mini Orca (Small)",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"}
    ]
)

print(completion.choices[0].message)
"""

import openai

openai.api_base = "http://localhost:4891/v1"
#openai.api_base = "https://api.openai.com/v1"

openai.api_key = "not needed for a local LLM"

# Set up the prompt and other parameters for the API request
prompt = "Who is Michael Jordan?"

model = "gpt-3.5-turbo"
#model = "mpt-7b-chat"
# model = "gpt4all-j-v1.3-groovy"

# Make the API request
response = openai.Completion.create(
    model=model,
    prompt=prompt,
    max_tokens=50,
    temperature=0.28,
    top_p=0.95,
    n=1,
    echo=True,
    stream=False
)

# Print the generated completion
print(response)
"""
