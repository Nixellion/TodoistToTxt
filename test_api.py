import todoist
import os
import yaml
import string

appdir = os.path.dirname(os.path.realpath(__file__))  # rp, realpath
datadir = os.path.join(appdir, "data")
# Read config
with open(os.path.join(appdir, 'config.yaml'), 'r') as f:
    config = yaml.load(f.read())

api = todoist.TodoistAPI(config['todoist_token'])
api.sync()



print (labels)
# for item in api.state['items']:
#     print (item['labels'])

def get_archival_text(api):
    projects = {}
    for project in api.state['projects']:
        projects[project['id']] = project['name']

    tasks = []

    for item in api.state['items']:
        text = f"({string.ascii_uppercase[4 - item['priority']]}) {item['content']} +{projects[item['project_id']]}"
        if item['due'] != None:
            text += f" due:{item['due']['date']}"
        tasks.append(text)

    archival_text = ''
    for task in sorted(tasks):
        archival_text += task + "\n"

    return archival_text
#     print(f"({string.ascii_uppercase[4 - item['priority']]}) {item['content']}")


def get_archival_text(api):
    tasks = []

    for item in api.state['items']:
        tasks.append(todoist_item_to_txt(item))

    archival_text = ''
    for task in sorted(tasks):
        archival_text += task + "\n"

    return archival_text