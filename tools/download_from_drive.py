from __future__ import print_function
import argparse
import os
import io
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError

SCOPES = ['https://www.googleapis.com/auth/drive']
API_NAME = 'drive'
API_VERSION = 'v3'


def arg_parse():
    """Parsing arguments"""
    parser = argparse.ArgumentParser(description="Script for downloading data from google drive")
    parser.add_argument('--token', required=True, type=str, metavar='TOKEN',
                        help='OAuth2 token file path')
    parser.add_argument('--file_id', required=True, type=str, metavar='TOKEN',
                        help='Download file id')
    parser.add_argument('--output_path', required=True, type=str, metavar='TOKEN',
                        help='Output file path')
    args = parser.parse_args()
    return args


def main():
    args = arg_parse()
    download_fileid = args.file_id
    file_output_path = args.output_path
    token = args.token

    creds = Credentials.from_authorized_user_file(token, SCOPES)
    service = build('drive', 'v3', credentials=creds)

    request = service.files().export_media(fileId=download_fileid, mimeType='text/csv')

    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False

    while not done:
        status, done = downloader.next_chunk()
        print("Download progress {0}".format(status.progress() * 100))

    fh.seek(0)

    with open(file_output_path, 'wb') as f:
        f.write(fh.read())
        f.close()


if __name__ == '__main__':
    main()
