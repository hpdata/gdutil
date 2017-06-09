#!/usr/bin/env python3

"""
List file names, their IDs and sizes in Google Drive
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


def list_files(drive, folder_id, gpattern='', parent=''):
    "Obtain a list of files and store into a dictionary"
    import fnmatch

    patterns = gpattern.split('/')

    if patterns[0] and '*' not in patterns[0] and \
       '?' not in patterns[0] and '[' not in patterns[0]:
        # Obtain the exact file
        file_list = drive.ListFile({'q': "'" + folder_id + "' in parents " +
                                    "and trashed=false and title='" +
                                    patterns[0] + "'"}).GetList()
    else:
        # Obtain the list of files
        file_list = drive.ListFile({'q': "'" + folder_id + "' in parents " +
                                    "and trashed=false"}).GetList()

    # put files into a dictionary
    ls = {}
    for file1 in file_list:
        if not patterns[0] or fnmatch.fnmatch(file1['title'], patterns[0]):
            if patterns.__len__() > 1:
                ls.update(list_files(drive, file1['id'],
                                     '/'.join(patterns[1:]),
                                     parent + file1['title'] + '/'))
            elif 'fileSize' in file1:
                ls[parent + file1['title']] = file1['id'], \
                    file1['fileSize'], file1['modifiedDate'], \
                    file1['shared'], file1['editable']
            else:
                ls[parent + file1['title']] = file1['id'], \
                    'd', file1['modifiedDate'], \
                    file1['shared'], file1['editable']

    return ls


if __name__ == "__main__":
    import os
    from pydrive.drive import GoogleDrive
    from gd_auth import authenticate
    from hurry.filesize import size as filesize

    args = parse_args(__doc__)

    folder_id = args.parent

    # Athenticate
    src_dir = os.path.dirname(os.path.realpath(__file__))
    gauth = authenticate(src_dir)

    # Create drive object
    drive = GoogleDrive(gauth)
    ls = list_files(drive, folder_id, args.pattern)

    try:
        use_color = os.environ["LS_COLORS"] != ""
    except:
        use_color = False

    for key, value in sorted(ls.items()):
        if ' ' in key:
            name = '"' + key + '"'
        else:
            name = key

        if value[3]:
            permission = 'w'
        else:
            permission = 'r'

        if args.long and value[1] == 'd':
            if use_color:
                print(permission + ' ' + value[2][:-5] +
                      '  dir  \033[0;34m' +
                      name + '\033[0m/' + ' => ' +
                      '  \033[0;32m' + value[0] + '\033[0m')
            else:
                print(permission + ' ' + value[2][:-5] + '  dir  ' +
                      name + '/' + ' => ' + value[0])
        elif value[1] == 'd':
            if use_color:
                print('\033[0;34m' + name + '\033[0m/')
            else:
                print(name + '/')
        elif args.long:
            print(permission + ' ' + value[2][:-5] +
                  '{:>5}'.format(filesize(int(value[1]))) + '  ' + name)
        else:
            print(name)
