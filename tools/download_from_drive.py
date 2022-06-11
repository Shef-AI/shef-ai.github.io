from __future__ import print_function
import argparse
import json
import os
import io
import sys
import calendar
from collections import OrderedDict
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError
from datetime import datetime

SCOPES = ['https://www.googleapis.com/auth/drive']
TOKEN_URI = "https://oauth2.googleapis.com/token"
API_NAME = 'drive'
API_VERSION = 'v3'
cals = {month: index for index, month in enumerate(calendar.month_name) if month}


def arg_parse():
    """Parsing arguments"""
    parser = argparse.ArgumentParser(description="Script for downloading data from google drive")
    parser.add_argument('--token', required=True, type=str, metavar='TOKEN',
                        help='OAuth2 token')
    parser.add_argument('--refresh_token', required=True, type=str, metavar='REFRESH_TOKEN',
                        help='refresh token')
    parser.add_argument('--client_id', required=True, type=str, metavar='CLIENT_ID',
                        help='client id')
    parser.add_argument('--client_secret', required=True, type=str, metavar='CLIENT_SECRET',
                        help='client secret')
    parser.add_argument('--folder_id', required=True, type=str, metavar='FOLDER_ID',
                        help='Download folder id')
    parser.add_argument('--output_path', required=True, type=str, metavar='OUTPUT',
                        help='Output folder name')
    args = parser.parse_args()
    return args


def download_files(service, download_fileid, file_output_path):
    request = service.files().get_media(fileId=download_fileid)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
        print("    Download progress {0}".format(status.progress() * 100))
    fh.seek(0)
    with open(file_output_path, 'wb') as f:
        f.write(fh.read())
        f.close()
    print(f"    The downloaded file is saved to : {file_output_path}")


def load_json_file(file_path):
    with open(file_path, "rb") as f:
        json_dict = json.load(f)
    return json_dict


def add_new_entry_from_drive(git_file_path, drive_file_path):
    git_dict = load_json_file(git_file_path)
    drive_dict = load_json_file(drive_file_path)
    git_entry_ids = set([git_entry["id"] for git_entry in git_dict])
    drive_entry_ids = set([drive_entry["id"] for drive_entry in drive_dict])
    add_new_ids = drive_entry_ids - git_entry_ids
    for new_id in add_new_ids:
        for drive_entry in drive_dict:
            if drive_entry["id"] == new_id:
                git_dict.append(drive_entry)
    return git_dict


def convert_datetime(item_dict):
    week, day, month, year = item_dict["date"].split()
    month = cals[month]
    date_str = f"{day}/{month}/{year[2:]} {item_dict['time']}"
    date_time = datetime.strptime(date_str, '%d/%m/%y %H:%M')
    return date_time


def main():
    args = arg_parse()
    folder_id = args.folder_id
    output_folder = args.output_path
    info = {"token": args.token,
            "refresh_token": args.refresh_token,
            "token_uri": TOKEN_URI,
            "client_id": args.client_id,
            "client_secret": args.client_secret,
            "scopes": SCOPES
            }

    creds = Credentials.from_authorized_user_info(info, SCOPES)
    service = build('drive', 'v3', credentials=creds)

    results = service.files().list(
        pageSize=1000, q=folder_id + " in parents", fields="nextPageToken, files(id, name, mimeType, trashed)").execute()
    items = results.get('files', [])
    if not items:
        print('No files found.')
    else:
        print('Files:')
        for item in items:
            print(f"\n    Name: {item['name']}, MimeType: {item['mimeType']}, TrashedStatus:{item['trashed']}")
            if not item['trashed']:
                try:
                    if item['mimeType'] == "application/json":
                        download_name = "{0}_{2}.{1}".format(*item['name'].rsplit('.', 1) + ["drive"])
                        file_output_path = "./json/" + download_name
                        repo_file_path = "./json/" + item['name']
                        download_files(service, item['id'], file_output_path)
                        print(f"    Update {item['name']} with latest data in drive")
                        update_output_dict = add_new_entry_from_drive(repo_file_path, file_output_path)
                        # sort items by published date order
                        update_output_dict.sort(key=lambda x: convert_datetime(x))
                        with open(repo_file_path, 'w') as fp:
                            json.dump(update_output_dict, fp, indent=4, ensure_ascii=False)
                        print(f"    Remove download file from drive: {file_output_path}")
                        os.remove(file_output_path)
                    elif item['mimeType'].startswith("image"):
                        file_output_path = f"./images/{output_folder}/" + item['name']
                        download_files(service, item['id'], file_output_path)
                    else:
                        continue
                except Exception as e:
                    print(f"    An exception occurred when trying to download file '{item['name']}' with error '{e}'")
                    sys.exit(1)


if __name__ == '__main__':
    main()
