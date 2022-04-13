from __future__ import print_function
import argparse
import json
import os
import io
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError

SCOPES = ['https://www.googleapis.com/auth/drive']
TOKEN_URI = "https://oauth2.googleapis.com/token"
API_NAME = 'drive'
API_VERSION = 'v3'


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
    parser.add_argument('--folder_id', required=True, type=str, metavar='FOLDER',
                        help='Download file id')
    parser.add_argument('--output_path', required=True, type=str, metavar='OUTPUT',
                        help='Output file path')
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


def main():
    args = arg_parse()
    folder_id = args.folder_id
    file_output_path = args.output_path
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
        pageSize=1000, q=folder_id+" in parents", fields="nextPageToken, files(id, name, mimeType, trashed)").execute()
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
                        file_output_path = "./json/" + item['name']
                    elif item['mimeType'].startswith("image"):
                        file_output_path = "./images/events/" + item['name']
                    else:
                        continue
                    download_files(service, item['id'], file_output_path)
                except Exception as e:
                    print(f"    An exception occurred when trying to download file '{item['name']}' with error '{e}'")


if __name__ == '__main__':
    main()
