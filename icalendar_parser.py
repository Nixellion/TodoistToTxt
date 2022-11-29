import requests
from io import BytesIO
from icalendar import Calendar, Event
from datetime import datetime
from pytz import UTC  # timezone
import todoist
import yaml
import os
import pytz


appdir = os.path.dirname(os.path.realpath(__file__))  # rp, realpath

with open(os.path.join(appdir, 'config.yaml'), 'r') as f:
    config = yaml.load(f.read())


local = pytz.timezone(config['local_timezone'])
naive = datetime.now()
local_dt = local.localize(naive, is_dst=None)
utc_dt_now = local_dt.astimezone(pytz.utc)


def sync_calendar(calendar_url, tag="todoisttotxt", priority=3):
    print(f"sync_calendar: {calendar_url}; {tag}; {priority}")
    response = requests.get(calendar_url)
    ical_data = BytesIO(response.content)

    ical = Calendar.from_ical(ical_data.read())

    api = todoist.TodoistAPI(config['todoist_token'])
    api.sync()

    api.commit()

    a = []

    # ['TZOFFSETFROM', 'URL', 'RRULE', 'ORGANIZER', 'X-WR-CALNAME',
    #  'RDATE', 'CALSCALE', 'RECURRENCE-ID', 'VERSION', 'UID', 'TZID',
    #  'X-WR-TIMEZONE', 'TZOFFSETTO', 'LAST-MODIFIED', 'TZURL', 'SUMMARY',
    #  'DTSTAMP', 'DTSTART', 'CATEGORIES', 'CREATED', 'TRANSP', 'METHOD',
    #  'TZNAME', 'LOCATION', 'ACTION', 'X-LIC-LOCATION', 'DESCRIPTION', 'TRIGGER',
    #  'ATTENDEE', 'DTEND', 'SEQUENCE', 'PRODID']

    for component in ical.walk():
        if component.name == "VEVENT":
            # print(component.get("uid"))
            # print(component.get("url"))
            # print(component.get("summary"))
            # print(component.get("description"))
            start = component.get("dtstart")
            end = component.get("dtend")
            stamp = component.get("dtstamp")
            ical_summary = component.get("summary")

            if start.dt < utc_dt_now:
                print(f"Skip {start.dt} < {utc_dt_now}: '{ical_summary}' ")
                continue

            print(f"START: {(start.dt)}; END: {end.dt}; STAMP: {stamp.dt}")
            ical_uid = component.get("uid")
            ical_uid_stamp = f"[UID: {ical_uid}]"

            ical_url = component.get("url")
            ical_description = component.get("description", "")

            first_line = ical_description.split("\n")[0]
            content = f"{tag.upper()}: {ical_summary}: {first_line} @{tag} "
            description = f"""{ical_description}

Link: {ical_url}

---
{ical_uid_stamp}"""
            skip = False
            for item in api.state['items']:
                if ical_uid_stamp in item['description']:
                    print(f"Exists, delete: {content}")
                    print(item)
                    item.delete()
                    api.commit()
                    break

            print(f"Adding task: {content}; {description}; {start.dt}")
            moscow = start.dt.astimezone(pytz.timezone('Europe/Moscow'))
            date_string = moscow.strftime(r"%Y.%m.%d at %H:%M")

            # api.items.add(content=content, description=description, due={'date': start.dt.strftime(r'%Y-%m-%dT%H:%M:%S'),
            #                                                             'is_recurring': False,
            #                                                             'lang': 'en',
            #                                                             'string': start.dt.strftime(r'%d %a %Y @ %H:%M'),
            #                                                             'timezone': None},

            #              project_id=None, priority=priority)

            api.items.add(content, project_id=None, date_string=date_string, description=description, priority=priority)
            api.commit()
    api.sync()


# api = todoist.TodoistAPI(config['todoist_token'])
# api.sync()

# api.items.get_by_id("14221847-6ff1-11ed-8b5d-44af2834ce21").delete()
# api.commit()