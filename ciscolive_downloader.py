"""Module providing download pdf file in ciscolive.com

This code is provided as-is, without any warranties or guarantees. Use at your own risk.
The author(s) are not responsible for any damages or issues that may arise from using this code.

API Usage
API: 'https://events.rainfocus.com/api/search'
      header: 'rfApiProfileId': '...'
      header: 'rfWidgetId': '...'
      POST
              'search.event': f'{eventid}',
              'type': 'session',
              'browserTimezone': 'Europe/Paris',
              'catalogDisplay': 'list'
              'from':10
      max support 500 items(i.e. from=490) returns from API
      return 10 items for each API call.
"""
import os
import json
import re
from pathlib import Path
from urllib.parse import urlparse
import requests

# disable SSL warning,if you use proxies
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Headers for API
headers = {
    'rfApiProfileId': 'HEedDIRblcZk7Ld3KHm1T0VUtZog9eG9',
    'rfWidgetId': 'M7n14I8sz0pklW1vybwVRdKrgdREj8sR'
}

# since session max than 500, we need split them by levels for downloading
cisco_levels = {'scpsSkillLevel_aintroductory',
                'scpsSkillLevel_bintermediate',
                'scpsSkillLevel_cadvanced',
                'scpsSkillLevel_dgeneral'}

# change here, you want downloaded,(event name, eventid, no use)
# you may get new eventid from ciscolive.com
cisco_events = [('2024 Las Vegas','1716482947962001yag9',885),
                ('2024 Amsterdam','1707169032930001EEu2',662),
                ('2023 Melbourne','1701901870185001qUFJ',194),
                ('2023 Las Vegas','1681761517718001tBvw',942),
                ('2023 Amsterdam','1675713481674001JK6C',620),
                ('2022 Melbourne','1669942290163001Ojog',196),
                ('2022 Las Vegas','1654953906132001zSK6',791),
                ('2021 Digital','1636046385175001F3fI',563),
                ('2020 Digital APJC','1636046385175003FWVY',60),
                ('2020 Digital','1636046385175002FlR0',669),
                ('2020 Barcelona','1636046385176001FR5R',556)
                ]

global_download_file_id = set()
GLOBAL_COUNTER = 0

def clean_filename(filename):
    """remove illegal filename char in windows
    """
    invalid_chars = r'[\\/:*?"<>|\'\t\r\n]'
    return re.sub(invalid_chars, '', filename)

def shorten_filename(full_path):
    """
    Shortens a full file path to be within the MAX_PATH limit of 260(we use 200) characters.    
    Args:
        full_path (str): The full path to the file, including the filename and extension.    
    Returns:
        str: The shortened full path.
    """
    # Get the directory and filename components
    dir_path = os.path.dirname(full_path)
    filename = os.path.basename(full_path)
    # Check if the full path exceeds the MAX_PATH(260) limit
    # i failed in 2xx chars, so change it to 200.
    if len(full_path) > 200:
        # Shorten the filename to fit within the limit
        max_filename_length = 200 - len(dir_path) - 1  # -1 for the file extension separator
        new_filename = f"{Path(filename).stem[:max_filename_length]}{Path(filename).suffix}"
        # Construct the new full path
        new_full_path = os.path.join(dir_path, new_filename)
        return new_full_path
    else:
        return full_path

def download_and_save_files(jsonobject):
    """download files.url if jsonobject contains
    """
    # pylint: disable-next=global-statement
    global GLOBAL_COUNTER
    #global global_download_file_id

    for section in jsonobject.get('sectionList', []):
        for item in section.get('items', []):
            event = item.get('event', '')
            title = item.get('title', '')
            files = item.get('files', [])
            GLOBAL_COUNTER = GLOBAL_COUNTER + 1

            if files:
                print(f"{GLOBAL_COUNTER} \tevent: {event}, title:{title} , downloading.")
            else:
                print(f"{GLOBAL_COUNTER} \tevent: {event}, title:{title} , no file, skip.")
                continue
            for file in files:
                url = file.get('url')
                if url:
                    base_name = os.path.basename(urlparse(url).path)
                    (filename,ext) = os.path.splitext(base_name)
                    title = clean_filename(title)

                    new_file_name = f"{event}--{filename}--{title}{ext}"

                    downloaded_file = shorten_filename("./download/" + new_file_name)

                    # check filename is already in ./download
                    if os.path.exists(downloaded_file):
                        # pylint: disable-next=line-too-long
                        print(f"{GLOBAL_COUNTER}\tevent:{event},file:{downloaded_file},already downloaded,skip.")
                    else:
                        #already downloaded in global_download_file_id
                        if filename not in global_download_file_id:
                            # downloading...
                            print(f"Downloading : {url}")
                            response = requests.get(url,verify=False,timeout=60)
                            if response.status_code == 200:
                                with open(downloaded_file, 'wb') as f:
                                    f.write(response.content)
                                print(f"Downloaded: {new_file_name}")
                                global_download_file_id.add(downloaded_file)
                            else:
                                print(f"Failed to download: {url}")
                        else:
                            # pylint: disable-next=line-too-long
                            print(f"{GLOBAL_COUNTER}\tevent:{event},file:{downloaded_file},already downloaded,skip.")

def download_event_one_level(eventid,levelid):
    r"""
    :levelid,  like "search.technicallevel: scpsSkillLevel_aintroductory"
    """
    # post data
    data_template = {
        'search.event': f'{eventid}',
        'type': 'session',
        'browserTimezone': 'Europe/Paris',
        'catalogDisplay': 'list',
        'search.technicallevel': f'{levelid}'}
    from_n = 0
    total_count = 500
    while from_n < total_count:
        data = data_template.copy()
        if from_n > 0:
            data['from'] = from_n
        response = requests.post('https://events.rainfocus.com/api/search',
                                headers=headers,
                                data=data,
                                verify=False,
                                timeout=60)  # disable SSL check
        if response.status_code == 200:
            data = json.loads(response.content)
            total_count = data.get('totalSearchItems', 0)
            download_and_save_files(data)
            from_n = from_n + 10
        else:
            break

def download_event(eventid):
    """download one event"""
    for levelid in cisco_levels:
        download_event_one_level(eventid,levelid)

if not os.path.exists('download'):
    # If it doesn't exist, create the directory
    os.makedirs('download')


def main():
    """main function"""
    for (_,eventid,_) in cisco_events:
        download_event(eventid)

if __name__ == '__main__':
    main()
