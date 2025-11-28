from openai import OpenAI
client = OpenAI()

response = client.responses.create(
    model="gpt-5.1",
    input="."
)

print(response.output_text)