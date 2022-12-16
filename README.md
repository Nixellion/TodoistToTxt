# TodoistToTxt

 A python script that exports your todoist tasks to txt file, formatted according to [todo.txt](https://github.com/todotxt/todo.txt) format.
 
 File can be copied to a specified directory and\or uploaded using webdav to the cloud, like Nextcloud.
 
 On run it will create 2 files in the specified locations (local folder and webdav like Nextcloud):
    - todoist_full.txt with full dump of all todo notes
    - file with specified name and specified filters through config.yaml
 
 
## Features

- Archive all your Todoist tasks into a todo.txt spec file
- Write specific project, today's tasks or inbox into a todo.txt spec file
- Create new Todoist tasks from calendars using CalDAV
- Create new Todoist tasks from Asana tasks
- Free reminder - script can send homeassistant notification for tasks marked with @notify tag (Limitations - if you change due date it wont notify you again on this same task, needs to be recreated)

## Requirements
- git
- python3
- pip3 (python3-pip)

Copy paste on debian systems to install requirements (remove sudo if on default debian, use with sudo on ubuntu and debian derivatives):

```
sudo apt install git python3-pip
```
 
## Installation 
 
- Clone repo anywhere you like
```
cd \opt
git clone https://github.com/Nixellion/TodoistToTxt.git
```
- Install requirements from requirements.txt
```
cd TodoistToTxt
pip3 install -r requirements.txt
```
- Copy example_config.yaml into config.yaml and adjust settings
```
cp example_config.yaml config.yaml
nano config.yaml
```
- todoist token is available in the web app, under preferences - integrations, API token
- Use cronjob or Task Scheduler to run this script as often as you like. Todoist supports up to 50 requests per minute or something like that.

### Cronjobs on Linux

[https://askubuntu.com/questions/2368/how-do-i-set-up-a-cron-job](https://askubuntu.com/questions/2368/how-do-i-set-up-a-cron-job)

[https://help.ubuntu.com/community/CronHowto](https://help.ubuntu.com/community/CronHowto)

You can also use Webmin to create cronjobs with UI.

# Todo

- Ability to create custom export templates (Jinja2? Or just format)


# Configuration

Configuration is done by creating and editing `config.yaml` file. An `example_config.yaml` file exists that can be renamed or copied.

```
webdav_url: drive.domain.com # Use None or False if you don't wish to copy to webdav
webdav_path: remote.php/webdav
webdav_directory: /Documents/Notes/
webdav_login: admin # dav login
webdav_password: password # dav pass
todoist_token: 'XXXXXXXXXXXXXXXXXXXXXXXXX'
todoist_project: 'Today'
todoist_append_inbox: True
max_items: 0
filename_output: todoist_todo.txt
export_file_as: False # Full path where to copy the file to. Must include filename
show_completed_tasks: yes
clean_up_completed_tasks: yes  # Auto remove completed tasks from Todoist. Currently required to stay as Yes. If you dont like it downgrade to previous versions and wait for an update.
todoist_inbox_hide_lowpriority: True  # Will hide priority level D
test_only: False
show_creation_date: no
show_completion_date: no
show_project_tag: no
show_due_date: yes
remove_completed_tasks: yes
debug: True
icalendar:  
  - url: https://calendar.google.com/xxxxxx  # CalDav URL of your calendar, Google, Yandex, Nextcloud, any that supports it
    priority: 4
    tag: my_calendar
    interval: 30
local_timezone: Europe/London 
local_timezone_offset: 0 # Because I'm lazy, please enter your time offset in hours for your timezone above, negative or positive number
homeassistant:
  hass_token: xxxxxxxxx # Home asssitant token which you can get from the UI under your user profile page (at least at the time of writing this)
  hass_url: http://192.168.1.2:8123 # Replace with your local or external home assistant url, *without* the trailing slash
  script_entity_id: script.my_notification # Script that will be triggered when event is processed. "title" and "message" attributes will be POSTed.
```


# Rainmeter skin

```
[Rainmeter]
Author=Michael Davydov
Update=1000
DynamicWindowSize=1

[MeasureLuaScript]
Measure=Script
ScriptFile="#CURRENTPATH#LuaTextFile.lua"
FileToRead=PATH\TO\YOUR\FILE.txt

[MeterDisplay]
Meter=String
MeasureName=MeasureLuaScript
W=1000
H=1360
FontFace=Ubuntu Light
FontSize=16
FontColor=216,222,233,255
SolidColor=20,20,20,1
AntiAlias=1
ClipString=1
StringEffect=Shadow
FontEffectColor=0,0,0,100
InlineSetting=Color | 191,97,106,255
InlinePattern=\(A\).*
InlineSetting2=Color | 94,129,172,255
InlinePattern2=\(C\).*
InlineSetting3=Color | 216,222,233,255
InlinePattern3=\(D\).*
InlineSetting4=Strikethrough
InlinePattern4=\nx.*
InlineSetting5=Color | 208,135,112,255
InlinePattern5=\(B\).*
InlineSetting6=Color | 235,203,139,255
InlinePattern6=(due:)(.*)
InlineSetting7=Case | Upper
InlinePattern7=(due:)(.*)
```


# ToDo:

- Make two versions of the script - one that will continue working as Cronjob and another that runs as a daemon with extra features and better responsiveness