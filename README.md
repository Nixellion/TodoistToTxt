# TodoistToTxt

 A python script that exports your todoist tasks to txt file, formatted according to [todo.txt](https://github.com/todotxt/todo.txt) format.
 
 File can be copied to a specified directory and\or uploaded using webdav to the cloud, like Nextcloud.
 
 
 
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

- Currently it can only publish to webdav and into a file that's located in the same folder as the script. Improve to support custom txt location on the filesystem, as well as more cloud providers.
- From todo.txt spec it currently only supports priority, which should be improved
- Ability to create custom export templates (Jinja2? Or just format)


# Configuration

Configuration is done by creating and editing `config.yaml` file. An `example_config.yaml` file exists that can be renamed or copied.

```
webdav_url: drive.domain.com # Use None or False if you don't wish to copy to webdav
webdav_path: remote.php/webdav
webdav_directory: /Documents/Notes/
webdav_login: admin # dav login
webdav_password: password # dav pass
todoist_token: '00000000000000000000000000000'
todoist_project: 'Inbox'
max_items: 0
filename_output: todoist_todo.txt
copy_file_to: False # Full path where to copy the file to. Can include filename or just a directory.
show_completed_tasks: yes
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
