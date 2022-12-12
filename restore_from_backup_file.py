'''
WARNING!

Use at your own risk.
This may not work properly in all cases.
For example it does not support spaces in project names!
'''
import os
import re
from todoist_api import TodoistAPI
import yaml
import time
appdir = os.path.dirname(os.path.realpath(__file__))

with open(os.path.join(appdir, 'config.yaml'), 'r') as f:
    config = yaml.load(f.read())
api = TodoistAPI(config['todoist_token'])


restore_txt_fp = os.path.join(appdir, "restore.txt")

pattern = r"^(?:\((?P<priority>[A-Z])\)\ )?(?P<todo>.+)\ (?:\+(?P<proname>[a-zA-Z0-9]+)(?:\#(?P<pronum>[0-9]+))?)\ ?(?:\$(?P<startd>2[0-1][0-9]{2}\-(?:0[0-9]|1[0-2])\-(?:[0-2][0-9]|3[0-1])))?"

with open(restore_txt_fp, "r", encoding="utf-8") as f:
    data = f.read()
data = data.replace(" due:", " $")

priority = "DCBA"

projects = {}
for project in api.get_items("projects"):
    projects[project['name']] = project['id']

for line in data.split("\n"):
    if not line.strip():
        continue

    print("---")
    print(line)
    match = re.match(pattern, line)
    if match:
        d = match.groupdict()
        task_data = {}
        task_data['content'] = d.get('todo')
        task_data['description'] = ''
        task_data['priority'] =  priority.index(d.get('priority', "D")) + 1
        if d.get('proname', False):
            task_data['project_id'] = projects[d['proname']]
        if d.get('startd', False):
            task_data['date_string'] = d.get('startd')

        api.add_item(task_data)

        time.sleep(3)
    else:
        print(f"NO MATCH FOUND FOR: {line}")
