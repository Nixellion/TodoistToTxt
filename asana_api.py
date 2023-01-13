import os
import yaml
import requests
from uuid import uuid4
from functools import wraps
from datetime import datetime, timedelta

appdir = os.path.dirname(os.path.realpath(__file__))  # rp, realpath

_asana_cache = {}
def _cache(cache_id):
    def decorator(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            if cache_id in _asana_cache:
                return _asana_cache[cache_id]
            return function(*args, **kwargs)
        return wrapper
    return decorator

class AsanaAPI():
    def __init__(self, token) -> None:
        self.headers = {
            "Authorization": f"Bearer {token}",
            "content-type": "application/json",
        }

        self._state_cache = {} 

    

    @_cache("tasks_summary")
    def get_tasks_summary(self, task_params):
        task_params['workspace'] = self.get_workspace_by_name(task_params['workspace'])['gid']
        task_params['assignee'] = self.get_user_id_by_name(task_params['assignee'])['gid']
        task_params['completed_since'] = datetime.now().strftime(r"%Y-%m-%d")
        tasks = requests.get("https://app.asana.com/api/1.0/tasks", headers=self.headers,
        params=task_params
        ).json()
        return tasks['data']

    @_cache("tasks")
    def get_tasks(self, task_params):
        tasks_summary = self.get_tasks_summary(task_params)
        tasks = []
        for task_summary in tasks_summary:
            tasks.append(
                requests.get(f"https://app.asana.com/api/1.0/tasks/{task_summary['gid']}", headers=self.headers).json()['data']
            )
        return tasks

    @_cache("workspaces")
    def get_workspaces(self):
        workspaces = requests.get("https://app.asana.com/api/1.0/workspaces", headers=self.headers).json()
        return workspaces['data']

    def get_workspace_by_name(self, workspace_name):
        workspaces = self.get_workspaces()
        for workspace in workspaces:
            if workspace['name'] == workspace_name:
                return workspace

    @_cache("users")
    def get_users(self):
        users = requests.get("https://app.asana.com/api/1.0/users", headers=self.headers).json()
        return users['data']

    def get_user_id_by_name(self, user_name):
        users = self.get_users()
        for user in users:
            if user['name'] == user_name:
                return user


        

    # def add_task(self,)
if __name__ == "__main__":
    # Testing
    with open(os.path.join(appdir, 'config.yaml'), 'r') as f:
        config = yaml.safe_load(f.read())
    print(AsanaAPI(config['asana'][0]['personal_access_token']).get_workspaces())

    # for task in AsanaAPI(config['asana'][0]['personal_access_token']).get_tasks(config['asana'][0]['task_params']):
    #     print(task)