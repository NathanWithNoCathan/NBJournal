from openai import OpenAI
import os

# get api key from file
api_key = open("api_key.txt").read().strip()
os.environ["OPENAI_API_KEY"] = api_key

client = OpenAI(api_key=api_key)

response = client.responses.create(
    model="gpt-5.1",
    input="Solve 5x+4=0 for x.",
)

print(response.output_text)