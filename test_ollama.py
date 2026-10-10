from ollama import chat

response = chat(
    model="qwen3:8b",
    messages=[
        {
            "role": "user",
            "content": "Explain what a football goalkeeper does in one sentence.",
        }
    ],
)

print(response.message.content)