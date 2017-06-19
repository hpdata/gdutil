#!/usr/bin/env python

"""
List file names, their IDs and sizes in Google Drive
"""

from __future__ import print_function


def parse_args(description):
    "Parse command-line arguments"

    import argparse
    import os

    # Process command-line arguments
    parser = argparse.ArgumentParser(description=description)

    parser.add_argument('-p', '--parent',
                        help='ID of the Google Drive folder to containt file',
                        default="root")

    parser.add_argument('-r', '--recursive',
                        help='List files recursively.',
                        default=False,
                        action='store_true')

    parser.add_argument('-l', '--long',
                        help='Print in long format, including fileID and size',
                        action="store_true",
                        default=False)

    parser.add_argument('-s', '--sort-by-size',
                        help='Sort by file size, largest first',
                        action="store_true",
                        default=False)

    parser.add_argument('-t', '--sort-by-time',
                        help='Sort by modification time, newest first',
                        action="store_true",
                        default=False)

    parser.add_argument('-n', '--sort-by-name',
                        help='Sort by names alphabetically with each folder',
                        action="store_true",
                        default=False)

    parser.add_argument('-e', '--sort-by-extension',
                        help='Sort by filename extensions',
                        action="store_true",
                        default=False)

    parser.add_argument('-c', '--config',
                        help='Configuration directory containing the ' +
                        ' credential. The default is ~/.config/gdutil/.',
                        default="")

    parser.add_argument('-C', '--color',
                        help='Use color for output. Default is on of LS_COLORS is defined.',
                        dest='use_color',
                        action='store_true',
                        default=None)

    parser.add_argument('-N', '--no-color',
                        help='Do not use color for output. Default is on of LS_COLORS is defined.',
                        dest='use_color',
                        action='store_false',
                        default=None)

    parser.add_argument('-q', '--quiet',
                        help='Suppress output.',
                        default=False,
                        action='store_true')

    parser.add_argument('-i', '--id', dest='ids',
                        nargs='+',
                        help='List of file or folder IDs.')

    parser.add_argument('patterns', metavar='NAME_PATTERN',
                        nargs='*',
                        help='List of file names or Unix filename patterns. ' +
                        '(Each name pattern must be enclosed in quotes).')

    args = parser.parse_args()
    args.unsorted = not args.sort_by_name and not args.sort_by_size and \
        not args.sort_by_time and not args.sort_by_extension

    if args.use_color is None:
        try:
            args.use_color = os.environ["TERM"].find('xterm') >= 0 or \
                os.environ["LS_COLORS"] != ""
        except:
            args.use_color = False

    return args


def proc_file(drive, file1, parent, dirs, ls, metadata,
              callback, callback_args, recursive):
    """
    Process a particular file.
    """

    name = parent + file1['title']

    # Detect duplicate entries
    duplicate = file1['id'] in ls
    isdir = 'fileSize' not in file1

    if dirs.__len__() == 1:
        if duplicate:
            alias = ls[file1['id']]['name']
            if name == alias:
                # Try duplicate
                return
            else:
                # aliasse to the same file
                pass
        else:
            alias = None

        if isdir:
            fileSize = -1
        else:
            fileSize = int(file1['fileSize'])

        # Append file into list
        val = {'id': file1['id'],
               'name': name,
               'fileSize': fileSize,
               'alias': alias,
               'fileobj': file1}

        for field in metadata:
            try:
                val[field] = file1[field]
            except:
                val[field] = ''

        ls[file1['id']] = val

        if callback:
            callback(val, *callback_args)

    # Do not recurse into duplicate entries
    if dirs.__len__() > 1 or \
            (isdir and recursive and not duplicate):
        list_files(drive=drive,
                   metadata=metadata,
                   parent_id=file1['id'],
                   patterns=['/'.join(dirs[1:])],
                   ls=ls,
                   parent=parent + file1['title'] + '/',
                   recursive=recursive,
                   callback=callback,
                   callback_args=callback_args)


def list_files(drive, parent_id, ids=None, patterns=None, parent='',
               ls=None, metadata=(), recursive=False,
               callback=None, callback_args=()):
    """
    Obtain a list of files and store into a dictionary.
    Also invoke callback if specified.

    Metadata lists the additional info besides name, id, fileSize, alias
    """

    import pydrive
    import fnmatch
    import sys
    import googleapiclient

    if ls is None:
        ls = {}
    if not ids:
        ids = []

    # Consider patterns only if id is not specified
    if not patterns:
        if not ids:
            patterns = ['']
        else:
            patterns = []

    # Process the list of file IDs
    for id in ids:
        try:
            file1 = drive.CreateFile({'id': id})
            file1.FetchMetadata()
            proc_file(drive, file1, parent, [''], ls, metadata,
                      callback, callback_args, recursive)
        except pydrive.files.ApiRequestError:
            sys.stderr.write('Invalid file ID %s\n' % id)

    # Process the list of file name patterns
    for pattern in patterns:
        dirs = pattern.split('/')

        prefix = dirs[0]
        for c in ['*', '[', ']', '?']:
            start = prefix.find(c)
            if start >= 0:
                prefix = prefix[:start]

        exact_match = dirs[0].__len__() > 0 and prefix == dirs[0]

        file_list = []
        try:
            if exact_match:
                # Obtain the exact file
                file_list += drive.ListFile({'q': "'" + parent_id + "' in parents " +
                                             "and trashed=false and title='" +
                                             dirs[0] + "'"}).GetList()
            elif prefix:
                # Obtain the files starting with prefix
                file_list += drive.ListFile({'q': "'" + parent_id + "' in parents " +
                                             "and trashed=false and title contains '" +
                                             prefix + "'"}).GetList()
            else:
                # Obtain the list of files
                file_list += drive.ListFile({'q': "'" + parent_id + "' in parents " +
                                             "and trashed=false"}).GetList()
        except googleapiclient.errors.HttpError:
            sys.stderr.write('Invalid parent ID %s.\n' % parent_id)
            break

        # put matching files and folders into a directory
        for file1 in file_list:
            if not dirs[0] or fnmatch.fnmatch(file1['title'], dirs[0]):
                proc_file(drive, file1, parent, dirs, ls, metadata,
                          callback, callback_args, recursive)

    return ls


def sizeof_fmt(num, suffix=''):
    for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Y', suffix)


def print_file(value, args):
    "Print a file or folder"

    if value['editable']:
        permission = 'w'
    else:
        permission = 'r'

    time = value['modifiedDate'][2:-5].replace('T', ' ')

    if value['alias']:
        base = value['alias']
    else:
        base = value['id']

    if args.long and value['fileSize'] < 0:
        if args.use_color:
            print(permission + ' ' + time +
                  '     dir \033[0;34m' +
                  value['name'] + '\033[0m/' + ' => ' +
                  '\033[0;32m' + base + '\033[0m')
        else:
            print(permission + ' ' + time + '     dir ' +
                  value['name'] + '/' + ' => ' + base)
    elif value['fileSize'] < 0:
        if args.use_color:
            print('\033[0;34m' + value['name'] + '\033[0m/')
        else:
            print(value['name'] + '/')
    elif args.long:
        if args.use_color:
            print(permission + ' ' + time +
                  '{:>8}'.format(sizeof_fmt(value['fileSize'])) + ' ' +
                  value['name'] + '\033[0m' + ' => ' +
                  '\033[0;32m' + base + '\033[0m')
        else:
            print(permission + ' ' + time +
                  '{:>8}'.format(sizeof_fmt(value['fileSize'])) + ' ' +
                  value['name'] + ' => ' + base)
    else:
        print(value['name'])


if __name__ == "__main__":
    import sys
    from pydrive.drive import GoogleDrive
    from gd_auth import authenticate

    args = parse_args(__doc__)

    # Athenticate
    gauth = authenticate(args.config)

    # Create drive object
    drive = GoogleDrive(gauth)

    if args.quiet:
        metadata = ()
    else:
        metadata = ('modifiedDate', 'editable', 'fileExtension')

    # List files
    if args.unsorted:
        ls = list_files(drive, parent_id=args.parent,
                        ids=args.ids, patterns=args.patterns,
                        metadata=metadata, recursive=args.recursive,
                        callback=print_file, callback_args=(args, ))
    else:
        ls = list_files(drive, parent_id=args.parent,
                        ids=args.ids, patterns=args.patterns,
                        metadata=metadata, recursive=args.recursive)

        if args.sort_by_name:
            files = sorted(ls.values(), key=lambda item: item['name'])
        elif args.sort_by_size:
            files = sorted(ls.values(), reverse=True,
                           key=lambda item: item['fileSize'])
        elif args.sort_by_extension:
            files = sorted(ls.values(),
                           key=lambda item: item['fileExtension'])
        else:
            files = sorted(ls.values(), reverse=True,
                           key=lambda item: item['modifiedDate'])

        for f in files:
            print_file(f, args)

    if not ls and args.patterns and not args.quiet:
        if args.use_color:
            sys.stderr.write('\033[0;31mNot found\033[0m\n')
        else:
            sys.stderr.write('Not found\n')
