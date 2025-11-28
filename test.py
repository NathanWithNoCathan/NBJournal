from openai import OpenAI
import os
client = OpenAI()

# get api key from file
api_key = open("api_key.txt").read().strip()
os.environ["OPENAI_API_KEY"] = api_key

response = client.responses.create(
    model="gpt-5.1",
    input="."
)

print(response.output_text)