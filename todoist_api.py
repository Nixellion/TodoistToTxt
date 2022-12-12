import os
import yaml
import requests
from uuid import uuid4

appdir = os.path.dirname(os.path.realpath(__file__))  # rp, realpath



def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

class TodoistAPI():
    def __init__(self, token) -> None:
        self.headers = {
            "Authorization": f"Bearer {token}",
            "content-type": "application/json",
        }

        self._state_cache = {}
        self.api_calls = 0

    def post(self, *args, **kwargs):
        self.api_calls += 1
        return requests.post(*args, **kwargs)

    def get(self, *args, **kwargs):
        self.api_calls += 1
        return requests.get(*args, **kwargs)

    def get_items(self, items_type="items", force_update=False):
        try:
            print(f"TODOIST get_items: {items_type}, {force_update}")
            if items_type not in self._state_cache or force_update:
                self.api_calls += 1
                response = self.post("https://api.todoist.com/sync/v9/sync", headers=self.headers, json={
                    "sync_token": "*",
                    "resource_types": [items_type]
                }
                ).json()
                items = response[items_type]
                self._state_cache[items_type] = items
            else:
                items = self._state_cache[items_type]
            return items
        except Exception as e:
            raise Exception(f"API ERROR ({e}): {response}")

    def delete_item(self, item):
        print(f"TODOIST delete_item: {item}")
        response = self.post("https://api.todoist.com/sync/v9/sync", headers=self.headers, json={
            "commands": [
                {
                    "type": "item_delete",
                    "uuid": str(uuid4()),
                    "args": {"id": item['id'] if isinstance(item, dict) else item}
                }
            ]
        }
        )

        return response

    def delete_items(self, items):
        print(f"TODOIST delete_items...")
        item_ids = []

        for item in items:
            item_ids.append(item['id'] if isinstance(item, dict) else item)

        print(item_ids)
        commands = []
        for item_id in item_ids:
            commands.append(
                {
                    "type": "item_delete",
                    "uuid": str(uuid4()),
                    "args": {"id": item_id}
                }
            )

        responses = []
        for commands_chunk in chunks(commands, 99):
            response = self.post("https://api.todoist.com/sync/v9/sync", headers=self.headers, json={
                "commands": commands_chunk
            }
            )
            responses.append(response.text)
        return responses

    def add_item(self, item_data):
        print(f"TODOIST add_item: {item_data}")
        task = self.post("https://api.todoist.com/sync/v9/items/add", headers=self.headers, json=item_data
                             ).text
        return task

    # def add_task(self,)
if __name__ == "__main__":
    # Testing
    with open(os.path.join(appdir, 'config.yaml'), 'r') as f:
        config = yaml.load(f.read())
    print(TodoistAPI(config['todoist_token']).get_items("projects"))