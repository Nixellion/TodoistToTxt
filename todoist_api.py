import os
import yaml
import requests
from uuid import uuid4
import time

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

    def put(self, *args, **kwargs):
        self.api_calls += 1
        return requests.put(*args, **kwargs)

    def delete(self, *args, **kwargs):
        self.api_calls += 1
        return requests.delete(*args, **kwargs)

    def get(self, *args, **kwargs):
        self.api_calls += 1
        return requests.get(*args, **kwargs)

    def get_items(self, items_type="items", force_update=False):
        response = None
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
                # if items_type == "items":
                #     items.extend(self.get_completed_tasks())
                self._state_cache[items_type] = items
            else:
                items = self._state_cache[items_type]
            return items
        except Exception as e:
            if response:
                raise Exception(f"API ERROR ({e}): {response}")
            else:
                raise Exception(f"API ERROR ({e})")

    def delete_item(self, item):
        print(f"- TODOIST delete_item: {item} - ", end="")
        item_id = item['id'] if isinstance(item, dict) else item
        response = self.delete("https://api.todoist.com/rest/v2/tasks/{}".format(item_id), headers=self.headers)
        if response.status_code != 204:
            print(f"Failed removing item {item_id}, API error: {response.text}")
        else:
            print("Success.")
        return response

    def delete_items(self, items):
        print(f"-- TODOIST delete_items:")
        item_ids = []

        for item in items:
            item_ids.append(item['id'] if isinstance(item, dict) else item)

        print(item_ids)
        print()
        responses = []
        for item_id in item_ids:
            response = self.delete_item(item_id)
            responses.append(response)
            time.sleep(0.5)
        return responses

    def delete_item_sync(self, item):
        print(f"TODOIST delete_item_sync: {item}")
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

    def delete_items_sync(self, items):
        print(f"TODOIST delete_items_sync...")
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

    def get_completed_tasks(self):
        completed_tasks = []
        for task in self.get("https://api.todoist.com/rest/v2/tasks", headers=self.headers).json():
            if task['is_completed'] == True:
                completed_tasks.append(task)
        return completed_tasks
        # return self.post("https://api.todoist.com/sync/v9/completed/get_all", headers=self.headers, json={
        #     "limit": 200
        # }).json()['items']
    
    def add_item(self, item_data, quick=False):
        print(f"TODOIST add_item: {item_data}")
        if quick:
            task = self.post("https://api.todoist.com/sync/v9/items/add", headers=self.headers, json=item_data
                             ).text
        else:

            # Adjust format of date string from quick_add format to sync format
            if 'date_string' in item_data:
                date_string = item_data.pop('date_string')
                item_data['due'] = {
                    'string': date_string
                }
            task = requests.post("https://api.todoist.com/sync/v9/sync", headers=self.headers, json={
                "commands": [
                    {
                        "type": "item_add",
                                "temp_id": str(uuid4()),
                                "uuid": str(uuid4()),
                                "args": item_data
                    }
                ]
            }
            ).text
        return task

    def move_item(self, item_id, project_id, remove_due_date=False):
        print(f"TODOIST move_item: {item_id} -> {project_id}")

        commands =[
                    {
                        "type": "item_move",
                                "uuid": str(uuid4()),
                                "args": {
                                    "id": item_id,
                                    "project_id": project_id
                                }
                    }
                ]

        if remove_due_date:
            commands.append({
                        "type": "item_update",
                                "uuid": str(uuid4()),
                                "args": {
                                    "id": item_id,
                                    "due": None
                                }
                    }
                )

        task = requests.post("https://api.todoist.com/sync/v9/sync", headers=self.headers, json={
                "commands": commands
            }
            ).text
        return task

    # def add_task(self,)
if __name__ == "__main__":
    # Testing
    import time
    with open(os.path.join(appdir, 'config.yaml'), 'r') as f:
        config = yaml.safe_load(f.read())

    api = TodoistAPI(config['todoist_token'])


    projects = {}
    for project in api.get_items("projects"):
        projects[project['id']] = project['name']

    completed_tasks = api.get_completed_tasks()
    print(completed_tasks)
    print(len(completed_tasks))
    # for task in completed_tasks:
    #     print()
    #     print(task['content'])
    #     print(projects[task['project_id']])
    #     api.delete_item(task['id'])
    #     api.delete_item(task['task_id'])
    #     break
    # print (api.delete_item("6491418785")) 
    # items = api.get_completed_tasks()
    # for item in items:
    #     print(item['content'])
    #     print(api.delete_completed_item(item).text)
    #     time.sleep(10)

    # items = api.get_items()
    # for item in items:
    #     print(item['id'])