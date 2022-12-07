import os
import yaml
import requests
from uuid import uuid4

appdir = os.path.dirname(os.path.realpath(__file__))  # rp, realpath


class TodoistAPI():
    def __init__(self, token) -> None:
        self.headers = {
            "Authorization": f"Bearer {token}",
            "content-type": "application/json",
        }

        self._state_cache = {} 

    def get_items(self, items_type="items", force_update=False):
        if items_type not in self._state_cache or force_update:
            items = requests.post("https://api.todoist.com/sync/v9/sync", headers=self.headers, json={
                    "sync_token": "*",
                    "resource_types": [items_type]
                }
                ).json()[items_type]
            self._state_cache[items_type] = items
        else:
            items = self._state_cache[items_type]
        return items

    def delete_item(self, item):
        response = requests.post("https://api.todoist.com/sync/v9/sync", headers=self.headers, json={
            "commands": [
                {
                    "type": "item_delete",
                    "uuid": str(uuid4),
                    "args": {"id": item['id'] if isinstance(item, dict) else item}
                }
            ]
        }
        )
        return response

    def add_item(self, item_data):
        task = requests.post("https://api.todoist.com/sync/v9/items/add", headers=self.headers, json=item_data
                ).text
        return task
        

    # def add_task(self,)
if __name__ == "__main__":
    # Testing
    with open(os.path.join(appdir, 'config.yaml'), 'r') as f:
        config = yaml.load(f.read())
    print(TodoistAPI(config['todoist_token']).get_items("projects"))