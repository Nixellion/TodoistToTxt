# TODO: Make Asana task tracking smarter, dont just batch delete everything, edit instead or smth, and remember if a task was compelted in todoist.
# IDEA: Store hashes of all tasks that were marked as compelted to file

import os
import shutil
import yaml
from todoist_api import TodoistAPI
from asana_api import AsanaAPI
import string
import tempfile
import requests
import traceback
import sys
import hashlib
import json
import re
# easywebdav python3 hack
import easywebdav.client
from datetime import date, datetime, timedelta
from pprint import PrettyPrinter
pp = PrettyPrinter()

easywebdav.basestring = str
easywebdav.client.basestring = str

import easywebdav

appdir = os.path.dirname(os.path.realpath(__file__))  # rp, realpath
datadir = os.path.join(appdir, "data")

if not os.path.exists(datadir):
    os.makedirs(datadir)

# Read config
with open(os.path.join(appdir, 'config.yaml'), 'r') as f:
    config = yaml.load(f.read())

# Fetch todoist items
todoist_api = TodoistAPI(config['todoist_token'])

labels = {}
for label in todoist_api.get_items("labels"):
    labels[label['id']] = label['name']

projects = {}
for project in todoist_api.get_items("projects"):
    projects[project['id']] = project['name']

# if config['debug']:
#     with open(os.path.join(appdir, "debug.json"), "w+", encoding="utf-8") as f:
#         f.write(pprint.pformat(api.state, indent=4))


def debug(text):
    if config['debug']:
        print(text)


today_path = os.path.join(datadir, datetime.now().strftime("%Y_%m_%d") + ".mem")

if not os.path.exists(today_path):
    with open(today_path, "w+", encoding="utf-8") as f:
        f.write("")


def today_memory():
    with open(today_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    return lines


def remember_task(task):
    lines = today_memory()
    if task not in lines:
        with open(today_path, "a+", encoding="utf-8") as f:
            f.write(task + "\n")
        print(f"Task '{task}' added to memory for today. ({lines})")
    else:
        print(f"Task '{task}' already remembered as completed for today.")


def todoist_item_to_txt(item):
    if item['checked'] == 0:
        text = ""
    else:
        text = "x "
    text += f"({string.ascii_uppercase[4 - item['priority']]}) {item['content']}"
    if item['project_id'] in projects:
        text += f" +{projects[item['project_id']]}"
    else:
        print("=" * 80)
        print(f"WARNING: Project {item['project_id']} not found in projects")
        for k, v in projects.items():
            print(k, v)
        print("=" * 80)

    for label_id in item['labels']:
        if label_id in labels:
            text += f" @{labels[label_id]}"

    if config['show_due_date'] is True and item['due'] is not None:
        text += f" due:{item['due']['date']}"

    return text


def completed_today():
    with open(today_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    tasks = 0
    for line in lines:
        if line.strip():
            tasks += 1
    return tasks


def get_project_id(name):
    project_id = None
    # Find required project
    for project in todoist_api.get_items("projects"):
        if project['name'] == name:
            project_id = project['id']
            break
    return project_id


def get_project_items(project_name):
    # Filter items
    # Filter completed out
    project_id = get_project_id(project_name)
    items = []
    for item in todoist_api.get_items():
        # print(item)
        select = False
        if project_name == "Today":
            if item['due'] != None:
                try:
                    due_date = datetime.strptime(item['due']['date'], "%Y-%m-%d").date()
                except:
                    try:
                        due_date = datetime.strptime(item['due']['date'], "%Y-%m-%dT%H:%M:%S").date()
                    except:
                        due_date = datetime.strptime(item['due']['date'], "%Y-%m-%dT%H:%M:%SZ").date()
                        due_date += timedelta(hours=config['local_timezone_offset'])

                now_date = datetime.now().date()
                date_check = due_date <= now_date
                # debug(f"Check due date: {due_date} <= {now_date} = {date_check};")
                if date_check:
                    select = True

        elif item['project_id'] == project_id:
            select = True

        if select:
            if config['max_items'] != 0 and len(items) > int(config['max_items']) - 1:
                break
            item_text = todoist_item_to_txt(item)

            if item['checked'] == 0 or config['show_completed_tasks']:
                items.append(item_text)

            # Cleanup completed tasks
            if config['remove_completed_tasks'] and item['checked'] == 1:
                remember_task(item['content'])
                if config['clean_up_completed_tasks']:
                    print(f"Deleting task '{item['content']}'")
                    todoist_api.delete_item(item)
            elif item['checked'] != 1 and item['checked'] != 0:
                print("Something's not right, did Todoist change API? item['checked'] is not 0 or 1:")
    return items


def text_from_items(items, filter_out=[], hide_low_priority=False):
    # Create output text
    output_text = ""
    for i in sorted(items):
        # print (i)
        if i not in filter_out and "(D) " not in i:
            output_text += i + "\n"
    return output_text


def generate_output_text():
    project_items = get_project_items(config['todoist_project'])
    output_text = text_from_items(project_items)
    inbox_text = text_from_items(get_project_items("Inbox"), filter_out=project_items,
                                 hide_low_priority=config['todoist_inbox_hide_lowpriority'])
    if config['todoist_append_inbox']:
        output_text = f'TODAY (Done: {completed_today()}):\n\n{output_text}\n\nINBOX:\n\n{inbox_text}'
    return output_text


def get_archival_text(api: TodoistAPI):
    tasks = []

    for item in api.get_items():
        tasks.append(todoist_item_to_txt(item))

    archival_text = ''
    for task in sorted(tasks):
        archival_text += task + "\n"

    return archival_text


def extract_data_from_description(description):
    print(f"Extracting data from: {description}")
    data = ""
    extract = False
    for line in description.split("\n"):
        if line.strip() == "--- TodoistToTxt Data End ---":
            extract = False
        if extract:
            data += line + "\n"
        if line.strip() == "--- TodoistToTxt Data ---":
            extract = True
    if not data:
        return_data = None
    else:
        return_data = yaml.safe_load(data)
    print(f"Extracted data: {return_data}")
    return return_data


def data_dumps(data):
    data_string = yaml.safe_dump(data)
    return f"""
```
--- TodoistToTxt Data ---
{data_string}
--- TodoistToTxt Data End ---
```

"""


from copy import copy


def generate_description(asana_task, task_data, task_type="start"):
    task_data = copy(task_data)
    task_data['task_type'] = task_type
    task_data_string = data_dumps(task_data)
    description = f"""{asana_task['notes']}

Link: {asana_task['permalink_url']}

{task_data_string}"""
    return description


if __name__ == "__main__":
    # TODO Make 'type' selection work
    # region ical
    import icalendar_parser
    # ICalendar sync
    for id, icalendar_data in enumerate(config['icalendar']):
        ical_cache_time_format = r"%Y.%m.%d %H:%M"
        ical_mem_path = os.path.join(appdir, "data", f"icalendar_{id}.date")
        if not os.path.exists(ical_mem_path):
            with open(ical_mem_path, "w+") as f:
                f.write((datetime.now() - timedelta(days=1)).strftime(ical_cache_time_format))

        with open(ical_mem_path, "r") as f:
            last_check = datetime.strptime(f.read(), ical_cache_time_format)

        if datetime.now() - last_check > timedelta(minutes=int(icalendar_data['interval'])):
            print(f"Checking calendar: {icalendar_data['tag']}")
            icalendar_parser.sync_calendar(
                calendar_url=icalendar_data['url'],
                tag=icalendar_data['tag'],
                tags=icalendar_data.get("tags", []),
                priority=icalendar_data['priority']
            )

            with open(ical_mem_path, "w+") as f:
                f.write(datetime.now().strftime(ical_cache_time_format))
        else:
            print(f"Skip checking calendar, too soon: {icalendar_data['tag']}")
    # endregion

    # region Asana
    for id, asana_profile in enumerate(config['asana']):
        asana_cache_time_format = r"%Y.%m.%d %H:%M"
        asana_mem_path = os.path.join(appdir, "data", f"asana_{id}.date")
        if not os.path.exists(asana_mem_path):
            with open(asana_mem_path, "w+") as f:
                f.write((datetime.now() - timedelta(days=1)).strftime(asana_cache_time_format))

        with open(asana_mem_path, "r") as f:
            last_check = datetime.strptime(f.read(), asana_cache_time_format)

        if datetime.now() - last_check > timedelta(minutes=int(asana_profile['interval'])):
            asana_api = AsanaAPI(asana_profile['personal_access_token'])
            asana_tag = asana_profile['tag']
            asana_tags = asana_profile.get('tags', [])
            asana_tags.append(asana_tag)
            asana_tasks = asana_api.get_tasks(asana_profile['task_params'])
            for asana_task in asana_tasks:
                start_date = datetime.strptime(
                    asana_task['start_on'], r"%Y-%m-%d") if asana_task.get('start_on', False) else None
                due_date = datetime.strptime(
                    asana_task['due_on'], r"%Y-%m-%d") if asana_task.get('due_on', False) else None
                if due_date and due_date < datetime.now():
                    continue

                new_task_data = {
                    "uid": f"asana_{asana_task['gid']}"
                }
                todoist_tasks = todoist_api.get_items()

                # TODO: Remember completed tasks and ignore them later
                remove_tasks = []
                for todoist_task in todoist_tasks:
                    task_data = extract_data_from_description(todoist_task['description'])
                    if task_data and task_data['uid'] == new_task_data['uid']:
                        print(f"Removing task, part of Asana Sync: {asana_task['name']}")
                        remove_tasks.append(todoist_task)
                print(todoist_api.delete_items(remove_tasks))

                if start_date and start_date.date() >= datetime.now().date():
                    content = f"{asana_tag.upper()} - START TASK: {asana_task['name']}" # @{asana_tag} "
                    # for _tag in asana_tags:
                    #     content += f"@{_tag} "

                    # TODO: Use `html_notes` with html to markdown
                    description = generate_description(asana_task, new_task_data, "start")
                    todoist_api.add_item(
                        {
                            "content": content,
                            "description": description,
                            "date_string": start_date.strftime(r"%Y.%m.%d"),
                            "priority": asana_profile['priority'],
                            "labels": asana_tags
                        }
                    )

                if due_date and due_date.date() >= datetime.now().date():
                    content = f"{asana_tag.upper()} - FINISH TASK: {asana_task['name']} @{asana_tag}"

                    # TODO: Use `html_notes` with html to markdown
                    description = generate_description(asana_task, new_task_data, "finish")
                    todoist_api.add_item(
                        {
                            "content": content,
                            "description": description,
                            "date_string": due_date.strftime(r"%Y.%m.%d"),
                            "priority": asana_profile['priority'],
                            "labels": asana_tags
                        }
                    )

                if start_date and due_date:
                    # CREATE "WORK ON TASK:"
                    delta = due_date - start_date
                    for i in range(1, delta.days):
                        day = start_date + timedelta(days=i)
                        if day.date() >= datetime.now().date():

                            content = f"{asana_tag.upper()} - WORK ON TASK: {asana_task['name']} @{asana_tag} "

                            # TODO: Use `html_notes` with html to markdown
                            description = generate_description(asana_task, new_task_data, "work")
                            todoist_api.add_item(
                                {
                                    "content": content,
                                    "description": description,
                                    "date_string": day.strftime(r"%Y.%m.%d"),
                                    "priority": asana_profile['priority'],
                                    "labels": asana_tags
                                }
                            )
            with open(asana_mem_path, "w+") as f:
                f.write(datetime.now().strftime(asana_cache_time_format))
        else:
            print(f"Skip checking Asana, too soon: {asana_profile['tag']}")

    # endregion

    # region Notifier
    def notifier_task_hash(task, label=""):
        string = json.dumps(task)
        string += label
        return hashlib.sha256(string.encode("utf-8")).hexdigest()

    if "homeassistant" in config:
        print("Running HomeAssistant notifier...")
        notified_filepath = os.path.join(appdir, 'data', 'notified.dat')
        if os.path.exists(notified_filepath):
            with open(notified_filepath, "r") as f:
                notified = f.read().split("\n")
        else:
            notified = []
        for item in todoist_api.get_items():
            # print(f"Notify? ({item['content']})")
            try:
                notify_regex = r"notify(?P<threshold>.+)?"
                # if len(item['labels']) == 0:
                #     print("No labels in this task.")
                for label in item['labels']:
                    match = re.match(notify_regex, label)
                    if match and item['due'] and item['due'] != None:
                        threshold = match.groupdict().get("threshold", None)
                        if threshold is None:
                            threshold = config['notifier_threshold_minutes']
                        notify_delta = timedelta(minutes=int(threshold))
                        item_hash = notifier_task_hash(item, label)
                        if item_hash in notified:
                            print(f"Already notified task: {item['content']}")
                            continue

                        # TODO This is used twice might need to turn into function, the only difference is .date() in the end
                        try:
                            due_date = datetime.strptime(item['due']['date'], "%Y-%m-%d")
                        except:
                            try:
                                due_date = datetime.strptime(item['due']['date'], "%Y-%m-%dT%H:%M:%S")
                            except:
                                due_date = datetime.strptime(item['due']['date'], "%Y-%m-%dT%H:%M:%SZ")
                                due_date += timedelta(hours=config['local_timezone_offset'])

                        now = datetime.now()
                        from_date = due_date - notify_delta
                        if from_date < now < due_date:
                            print(f"Trying to notify about due task: {item['content']}")
                            try:
                                url = f"{config['homeassistant']['hass_url']}/api/services/script/turn_on"
                                headers = {
                                    "Authorization": f"Bearer {config['homeassistant']['hass_token']}",
                                    "content-type": "application/json",
                                }
                                response = requests.post(url, headers=headers, json={
                                    "entity_id": config['homeassistant']['script_entity_id'],
                                    "variables":
                                    {
                                        "title": f"Todoist Item is Due!",
                                        "message": item['content'],
                                        "clickAction": f"https://todoist.com/showTask?id={item['id']}" # Set url to open todoist item,
                                    }
                                }
                                )
                                with open(notified_filepath, "a+") as f:
                                    f.write(item_hash + "\n")
                            except Exception as e:
                                print("ERROR!", e)
                    else:
                        print(f"Label did not match notify label pattern: {label} ({notify_regex})")

            except Exception as e:
                print(e)
                traceback.print_exc()

    # endregion
    local_filepath = os.path.join(appdir, config['filename_output'])

    output_text = generate_output_text()
    backup_text = get_archival_text(todoist_api)

    debug(output_text)

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

    print(f"TodoistAPI calls made: {todoist_api.api_calls}")

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

        # Write filtered file
        with tempfile.NamedTemporaryFile(mode="w+", encoding='utf-8', delete=False) as tmp:
            tmp.write(output_text)
            tmp_fp = tmp.name

        webdav.upload(tmp_fp, "{}/{}".format(config['webdav_directory'], config['filename_output']))
        os.remove(tmp_fp)

        # Write full backup file
        with tempfile.NamedTemporaryFile(mode="w+", encoding='utf-8', delete=False) as tmp:
            tmp.write(backup_text)
            tmp_fp = tmp.name

        webdav.upload(tmp_fp, "{}/{}".format(config['webdav_directory'], "todoist_full.txt"))

        backups_dir = os.path.join(appdir, "backups")
        if not os.path.exists(backups_dir):
            os.makedirs(backups_dir)

        index = datetime.now().strftime(r"%Y_%m_%d_%H_%M_%S")
        backup_fp = os.path.join(backups_dir, f"backup_{index}.txt")
        shutil.copy(tmp_fp, backup_fp)
        backups = os.listdir(backups_dir)
        if len(backups) > config['max_backups']:
            os.remove(os.path.join(backups_dir, sorted(backups)[0]))

        os.remove(tmp_fp)
