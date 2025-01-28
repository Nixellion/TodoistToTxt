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
import time
import timeago
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
    config = yaml.safe_load(f.read())

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
        print(f"Task '{task}' added to memory for today.")
    else:
        print(f"Task '{task}' already remembered as completed for today.")


def todoist_item_to_txt(item):
    if item['checked'] is False:
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


def get_item_due_date(item, as_date=True):
    if item['due'] is None:
        return None
    due_date = cast_to_datetime(item['due']['date'])
    if as_date:
        return due_date.date()
    return due_date

def get_project_items(project_name, as_text=True, adhere_to_limits=True):
    # Filter items
    # Filter completed out
    project_id = get_project_id(project_name)
    items = []
    for item in todoist_api.get_items():
        # print(item)
        select = False
        if project_name == "Today":
            if item['due'] != None:
                due_date = get_item_due_date(item)

                now_date = datetime.now().date()
                date_check = due_date <= now_date
                # debug(f"Check due date: {due_date} <= {now_date} = {date_check};")
                if date_check:
                    select = True

        elif item['project_id'] == project_id:
            select = True

        if select:
            if adhere_to_limits and config['max_items'] != 0 and len(items) > int(config['max_items']) - 1:
                break

            if as_text is False:
                items.append(item)
            else:
                item_text = todoist_item_to_txt(item)

                if item['checked'] is False or config['show_completed_tasks']:
                    items.append(item_text)

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

def save_to_file(filepath, format, project, delete_originals):
    print(f"Save to file: {filepath} format: {format} project: {project} delete_originals: {delete_originals}")
    if format != "markdown":
        raise ValueError(f"Format {format} not supported")
    
    project_items = get_project_items(project, as_text=False, adhere_to_limits=False)
    if format == "markdown":

        item_template = """
# {title}

> **Labels**: `{labels}`
> **Due**: {due}
> **TodoTxt**: `{txt_format}`

{description}

---
"""
        for i in project_items:
            labels = ""
            for l in i['labels']:
                labels += f"`{l}` "
            new_text = item_template.format(
                title=i['content'],
                labels=labels,
                due=get_item_due_date(i),
                description=i['description'],
                txt_format=todoist_item_to_txt(i)
            )
            with open(filepath, "a+", encoding="utf-8") as f:
                f.write(new_text)

            if delete_originals:
                todoist_api.delete_item(i)

        


def get_archival_text(api: TodoistAPI):
    tasks = []

    for item in api.get_items():
        tasks.append(todoist_item_to_txt(item))

    archival_text = ''
    for task in sorted(tasks):
        archival_text += task + "\n"

    return archival_text


def extract_data_from_description(description):
    # print(f"Extracting data from: {description}")
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
    # print(f"Extracted data: {return_data}")
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


def send_notification(message, title=None, click_action = None):
    print(f"Trying to send notification: {message} | {title} | {click_action}")
    try:
        url = f"{config['homeassistant']['hass_url']}/api/services/script/turn_on"
        headers = {
            "Authorization": f"Bearer {config['homeassistant']['hass_token']}",
            "content-type": "application/json",
        }

        variables = {"message": message}
        if title:
            variables['title'] = title
        if click_action:
            variables['clickAction'] = click_action

        response = requests.post(url, headers=headers, json={
            "entity_id": config['homeassistant']['script_entity_id'],
            "variables": variables
        }
        )
        return response
    except Exception as e:
        print("ERROR!", e)

def process_inbox_backlog(backlog_config):
    """Move old non-recurring tasks from Inbox to backlog project based on configuration settings."""
    inbox_id = get_project_id("Inbox")
    backlog_id = get_project_id(backlog_config['project'])
    
    if not inbox_id or not backlog_id:
        debug(f"Skipping inbox backlog processing - could not find {'Inbox' if not inbox_id else backlog_config['project']} project")
        return

    current_time = datetime.now()
    moved_count = 0

    for item in todoist_api.get_items():
        if item['project_id'] != inbox_id:
            continue
            
        # Skip if task is recurring
        if item.get('due') and item['due'].get('is_recurring'):
            continue
            
        try:
            created_date = cast_to_datetime(item.get('created_at', item['added_at']))
            
            days_old = (current_time - created_date).days
            
            if days_old > backlog_config['days_created']:
                due_date = get_item_due_date(item)

                if not due_date:
                    continue
                
                if (due_date - current_time).days > backlog_config['days_due']:
                    debug(f"Moving task to backlog: {item['content']}")
                    todoist_api.move_item(item['id'], backlog_id)
                    moved_count += 1
                    
        except Exception as e:
            debug(f"process_inbox_backlog: Error processing inbox item {item['content']}: {str(e)}")
            debug(item)
            
    if moved_count > 0:
        debug(f"Moved {moved_count} tasks from Inbox to {backlog_config['project']}")


def cast_to_datetime(date_string):
    try:
        due_date = datetime.strptime(date_string, "%Y-%m-%d")
    except:
        try:
            due_date = datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S")
        except:
            try:
                due_date = datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%SZ")
                due_date += timedelta(hours=config['local_timezone_offset'])
            except:
                due_date = datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S.%fZ")
                due_date += timedelta(hours=config['local_timezone_offset'])
    return due_date

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

                        due_date = cast_to_datetime(item['due']['date'])

                        now = datetime.now()
                        from_date = due_date - notify_delta
                        if from_date < now < due_date:
                            print(f"Trying to notify about due task: {item['content']}")
                            notification_result = send_notification(
                                item['content'],
                                f"Todoist Item Due {timeago.format(due_date, datetime.now())}!",
                                f"https://todoist.com/showTask?id={item['id']}"
                            )
                            if notification_result is not None:
                                with open(notified_filepath, "a+") as f:
                                    f.write(item_hash + "\n")
                    else:
                        print(f"Label did not match notify label pattern: {label} ({notify_regex})")

            except Exception as e:
                print(e)
                traceback.print_exc()

    delete_ids = []
    # region Task Expiration
    for item in todoist_api.get_items():
            # print(f"Notify? ({item['content']})")
            try:
                expire_regex = r"expire(?P<hours>.+)?"
                # if len(item['labels']) == 0:
                #     print("No labels in this task.")
                for label in item['labels']:
                    match = re.match(expire_regex, label)
                    if match:
                        expire_hours = match.groupdict().get("hours", None)
                        if expire_hours:
                            expire_delta = timedelta(hours=int(expire_hours))
                            due_date = cast_to_datetime(item['added_at'])
                            
                            if datetime.now() - due_date > expire_delta:
                                print(f"Querying task for deletion due to expiration label: '{str(item)}")
                                delete_ids.append(item['id'])
                                notification_result = send_notification(
                                    item['content'],
                                    f"Todoist Item Expired.",
                                    f"https://todoist.com/showTask?id={item['id']}"
                                )
                            break
                        else:
                            print(f"Task is marked to expire, but it's not due yet {label}: {str(item)}")

                    else:
                        print(f"Label did not match expire label pattern: {label} ({expire_regex})")
            except Exception as e:
                print(f"Failed processing expiration for task ({label}): {e}")

    # endregion

    # endregion
    local_filepath = os.path.join(appdir, config['filename_output'])

    output_text = generate_output_text()
    backup_text = get_archival_text(todoist_api)

    for stf in config.get("save_to_file", []):
        save_to_file(**stf)

    debug(output_text)

    for item in todoist_api.get_completed_tasks():
        if config['remove_completed_tasks']:
            remember_task(item['content'])
            if config['clean_up_completed_tasks']:
                print(f"Deleting task '{item['content']}'")
                delete_ids.append(item['task_id'])
            else:
                print(f"Config tells me to skip clean_up_completed_tasks: {item['content']}")


    if len(delete_ids) > 0:
        print("RESULT:")
        print (todoist_api.delete_items(delete_ids))


    # Move to backlog
    if config.get("auto_backlog", {}):
        process_inbox_backlog(config["auto_backlog"])

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
