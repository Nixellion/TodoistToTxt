import requests
import os
import yaml
import json
import re
from ollama import Client

appdir = os.path.dirname(os.path.realpath(__file__))

with open(os.path.join(appdir, 'config.yaml'), 'r') as f:
    config = yaml.safe_load(f.read())

ai_type = config['llm_tools']['use_ai_type']

def extract_json_from_output(text):
    """
    Extract JSON content from text that may contain other content.
    
    Args:
        text (str): The input text containing JSON
        
    Returns:
        dict: Parsed JSON object, or None if no valid JSON found
    """
    # Remove the <think> block if present
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    
    # Find JSON content between curly braces
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    
    if json_match:
        json_str = json_match.group(0)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return None
    
    return None

if 'llm_tools' in config:
    if ai_type == "openai":
        print("USING OPENAI AI SERVICE")
        _chat_completions_url = config['llm_tools']['openedai']['base_url'] + "/v1/chat/completions"

        def call_ai(system_message, user_message, as_json=True):
            payload = {
                "messages":[
                    { "role": "system", "content": system_message },
                    {
                        "role": "user",
                        "content": user_message,
                    },
                ]
            }
            response = requests.post(_chat_completions_url, json=payload)

            if response.status_code != 200:
                print(f"AI ERROR: {response.status_code} {response.text}")
                return None
            
            response_message = response.json()['choices'][0]['message']['content']

            if as_json:
                response_message = response_message.replace('```', "")
                response_message = extract_json_from_output(response_message)

            return response_message
    elif ai_type == "ollama":
        print("USING OLLAMA AI SERVICE")
        client = Client(host=config['llm_tools']['ollama']['host'])
        def call_ai(system_message, user_message, as_json=True):
            payload = {
                "model": config['llm_tools']['ollama']['model'],
                "messages":[
                    { "role": "system", "content": system_message },
                    {
                        "role": "user",
                        "content": user_message,
                    },
                ]
            }
            response = client.chat(**payload)

            response_message = response['message']['content']
            print(response_message)

            if as_json:
                response_message = response_message.replace('```', "")
                response_message = extract_json_from_output(response_message)

            return response_message
    
if __name__ == "__main__":
    system_message = "Your task is to analyze user's ToDo tasks and sort them into the following categories:\n\n"
    system_message += config['llm_tools']['smart_sort']['prompt']
    system_message += """\n\nIf no category fits, leave it in inbox.

Your reply must be in JSON in a form of:

```
{
"reasoning": "Think and provide reasoning for your decision",
"confidence": "How confident you are about your decision",
"category": "Category"
}
```
"""
    message = f"Sort this task:\n\nCode review for the new project on Friday at 10am. It's important and should be done as soon as possible."
    print(call_ai(system_message, message))