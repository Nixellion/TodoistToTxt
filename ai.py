import requests
import os
import yaml
import json

appdir = os.path.dirname(os.path.realpath(__file__))

with open(os.path.join(appdir, 'config.yaml'), 'r') as f:
    config = yaml.safe_load(f.read())
if 'llm_tools' in config:
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
            try:
                response_message = json.loads(response_message)
            except json.JSONDecodeError:
                return None

        return response_message
    
