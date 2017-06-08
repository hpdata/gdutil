#!/usr/bin/env python3

"""
List file names, their IDs and sizes in a Google Drive
"""


def parse_args(description):
    "Parse command-line arguments"

    import argparse

    # Process command-line arguments
    parser = argparse.ArgumentParser(description=description)

    parser.add_argument('-p', '--parent',
                        help='ID of the Google Drive folder to containt file',
                        default="root")

    parser.add_argument('-l', '--long',
                        help='Print in long format, including fileID and size',
                        action="store_true",
                        default=False)

    parser.add_argument('pattern',
                        nargs='?',
                        help='Unix file name pattern (must be in quotes)',
                        default='')

    args = parser.parse_args()
    return args


def list_files(drive, folder_id, glob='', parent=''):
    "Obtain a list of files and store into a dictionary"
    import fnmatch

    # Obtain the list of files
    file_list = drive.ListFile({'q': "'" + folder_id + "' in parents " +
                                "and trashed=false"}).GetList()
    patterns = glob.split('/')

    # put files into a dictionary
    ls = {}
    for file1 in file_list:
        if not patterns[0] or fnmatch.fnmatch(file1['title'], patterns[0]):
            if patterns.__len__() > 1:
                ls.update(list_files(drive, file1['id'],
                                     '/'.join(patterns[1:]),
                                     parent + file1['title'] + '/'))
            elif 'fileSize' in file1:
                ls[parent + file1['title']] = file1['id'], file1['fileSize']
            else:
                ls[parent + file1['title']] = file1['id'], 'directory'

    return ls


if __name__ == "__main__":
    import os
    from pydrive.drive import GoogleDrive
    from gd_auth import authenticate

    args = parse_args(__doc__)

    folder_id = args.parent

    # Athenticate
    src_dir = os.path.dirname(os.path.realpath(__file__))
    gauth = authenticate(src_dir)

    # Create drive object
    drive = GoogleDrive(gauth)
    ls = list_files(drive, folder_id, args.pattern)

    if args.long:
        for key, value in sorted(ls.items()):
            if ' ' in key:
                name = '"' + key + '"'
            else:
                name = key

            if value[1] == 'directory':
                print(name + ', ' +
                      'id:' + value[0] + ', ' + 'size: ' + value[1])
            else:
                print(name + ', ' +
                      'id:' + value[0] + ', ' + value[1])
    else:
        for key, value in sorted(ls.items()):
            if ' ' in key:
                print('"' + key + '"')
            else:
                print(key)
