import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get API key from environment variable
api_key = os.getenv("OPENROUTER_API_KEY")

response = requests.post(
  "https://openrouter.ai/api/v1/chat/completions",
  headers={
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
  },

  json={
    "model": "deepseek/deepseek-chat",
    "messages": [
      {"role": "user", "content": "What is the weather like in London?"},
    ],
    "provider": {
      "require_parameters": True
    },
    "response_format": {
      "type": "json_schema",
      "json_schema": {
        "name": "weather",
        "strict": True,
        "schema": {
          "type": "object",
          "properties": {
            "location": {
              "type": "string",
              "description": "City or location name",
            },
            "temperature": {
              "type": "number",
              "description": "Temperature in Celsius",
            },
            "conditions": {
              "type": "string",
              "description": "Weather conditions description",
            },
          },
          "required": ["location", "temperature", "conditions"],
          "additionalProperties": False,
        },
      },
    },
  },
)

data = response.json()
weather_info = data["choices"][0]["message"]["content"]
print(weather_info)