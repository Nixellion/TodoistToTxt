import os
import yaml
import todoist
import string
import tempfile
import sys
# easywebdav python3 hack
import easywebdav.client

easywebdav.basestring = str
easywebdav.client.basestring = str

import easywebdav

appdir = os.path.dirname(os.path.realpath(__file__))  # rp, realpath

# Read config
with open(os.path.join(appdir, 'config.yaml'), 'r') as f:
    config = yaml.load(f.read())

# Fetch todoist items
api = todoist.TodoistAPI(config['todoist_token'])
api.sync()

# Pprint for debug purposes
# from pprint import PrettyPrinter
# pp = PrettyPrinter(indent=4, width=10000)
# pp.pprint(api.state)
# input()

def get_project_id(name):
    project_id = None
    # Find required project
    for key, value in api.state.items():
        if key == 'projects':
            # print (value)
            for project in value:
                if project['name'] == name:
                    project_id = project['id']
                    break
            break
    return project_id

def get_project_items(project_name):
    # Filter items
    # Filter completed out
    project_id = get_project_id(project_name)
    items = []
    for item in api.state['items']:
        if item['project_id'] == project_id:
            if config['max_items'] != 0 and len(items) > int(config['max_items']) - 1:
                break
            if item['checked'] == 0:
                items.append("({}) {}".format(string.ascii_uppercase[4 - item['priority']], item['content']))
            elif item['checked'] == 1:
                if config['show_completed_tasks']:
                    items.append("x ({}) {}".format(string.ascii_uppercase[4 - item['priority']], item['content']))
            else:
                print("Something's not right, did Todoist change API? item['checked'] is not 0 or 1.")
    return items

def text_from_items(items, filter_out=[]):
    # Create output text
    output_text = ""
    for i in sorted(items):
        # print (i)
        if i not in filter_out:
            output_text += i + "\n"
    return output_text

def generate_output_text():
    project_items = get_project_items(config['todoist_project'])
    output_text = text_from_items(project_items)
    if config['todoist_append_inbox']:
        output_text = f'TODAY:\n\n{output_text}\n\nINBOX:{text_from_items(get_project_items("Inbox"), filter_out=project_items)}'
    return output_text

if __name__ == "__main__":
    # TODO Make 'type' selection work


    local_filepath = os.path.join(appdir, config['filename_output'])

    output_text = generate_output_text()

    # Copy if copy
    if config['export_file_as']:
        if os.path.exists(config['export_file_as']):
            with open(config['export_file_as'], 'r', encoding='utf-8', errors='ignore') as f:
                old_text = f.read()
            if output_text == old_text:
                print("No changes in todo list. Exit.")
                sys.exit()
        with open(config['export_file_as'], 'w+', encoding='utf-8', errors='ignore') as f:
            f.write(output_text)

    # Upload to webdav
    if config['webdav_url']:
        webdav = easywebdav.connect(config['webdav_url'], username=config['webdav_login'],
                                    password=config['webdav_password'],
                                    protocol='https', port=443, verify_ssl=False, path=config['webdav_path'])
        with tempfile.NamedTemporaryFile(mode="wb+", delete=False) as tmp:
            webdav.download("{}/{}".format(config['webdav_directory'], config['filename_output']), tmp)
            tmp_fp = tmp.name
        with open(tmp_fp, "r", encoding="utf-8") as f:
            old_text = f.read()
            if output_text == old_text:
                print("No changes in todo list. Exit.")
                os.remove(tmp_fp)
                sys.exit()

        with tempfile.NamedTemporaryFile(mode="w+", encoding='utf-8', delete=False) as tmp:
            tmp.write(output_text)
            tmp_fp = tmp.name



        webdav.upload(tmp_fp, "{}/{}".format(config['webdav_directory'], config['filename_output']))
        os.remove(tmp_fp)