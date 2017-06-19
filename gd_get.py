#!/usr/bin/env python

"""
Download a list of files from Google Drive.
"""

from __future__ import print_function

import sys
import hashlib
from gd_auth import authenticate
from gd_list import list_files
from progressbar import ProgressBar


def parse_args(description):
    "Parse command-line arguments"

    import argparse

    # Process command-line arguments
    parser = argparse.ArgumentParser(description=description)

    parser.add_argument('-p', '--parent',
                        help='ID of parent folder in Google Drive',
                        default="root")

    parser.add_argument('-r', '--recursive',
                        help='Download files recursively. It implies -O.',
                        default=False,
                        action='store_true')

    parser.add_argument('-o', '--outfile',
                        help='Output file name. Use -o - to output to stdout.',
                        default="")

    parser.add_argument('-O', '--remote',
                        help='Use remote filename as output file name.',
                        action='store_true',
                        default=False)

    parser.add_argument('-d', '--outdir',
                        help='Local parent directory path. ' +
                        'The default is current directory.',
                        default="")

    parser.add_argument('-P', '--preserve',
                        help='Preserve the directory structure locally. ' +
                        'It is overwrites the -o option.',
                        action="store_true",
                        default=False)

    parser.add_argument('-c', '--config',
                        help='Configuration directory containing the ' +
                        ' credential. The default is ~/.config/gdutil/.',
                        default="")

    parser.add_argument('-q', '--quiet',
                        help='Suppress information and error messages.',
                        default=False,
                        action='store_true')

    parser.add_argument('-i', '--id', dest='ids',
                        nargs='+',
                        help='List of file or folder IDs to be downloaded.')

    parser.add_argument('patterns', metavar='NAME_PATTERN',
                        nargs='*',
                        help='List of file names or Unix filename patterns. ' +
                        '(Each name pattern must be enclosed in quotes).')

    args = parser.parse_args()

    if args.outdir and args.outdir[-1] != '/':
        args.outdir = args.outdir + '/'

    return args


def md5chksum(fname):
    " Computes md5chksum of a local file "

    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def sizeof_fmt(num, suffix='Bps'):
    " Format size in human-readable format "

    for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
        if abs(num) < 1024.0:
            return "%3.1f %s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Y', suffix)


def download_file(file1, auth, args):
    "Download a given file"

    import sys
    import os
    import time
    from apiclient import http
    from apiclient import errors

    dirname, basename = os.path.split(file1['name'])

    if args.preserve:
        fname = args.outdir + dirname + '/' + basename
    elif args.outfile and args.outfile != '-':
        fname = args.outdir + args.outfile
    elif args.remote:
        fname = args.outdir + basename
    else:
        fname = '-'

    # If give file is a folder, create the directory locally
    fileSize = file1['fileSize']
    if fileSize < 0:
        if args.preserve and not os.path.isdir(fname):
            os.makedirs(fname)
        return

    if fname != '-' and os.path.isfile(fname):
        # Download file only if size is different or checksum is different
        # Compute chksum
        if os.path.getsize(fname) == fileSize and \
                md5chksum(fname) == file1['fileobj']['md5Checksum']:
            # Download the file
            if not args.quiet:
                sys.stderr.write("File %s is up to date.\n" % fname)
                sys.stderr.flush()

            return
    elif fname != '-' and args.preserve and \
            dirname and not os.path.isdir(dirname):
        # Create directory if not exist
        os.makedirs(dirname)

    # Download the file
    if not args.quiet:
        sys.stderr.write("Downloading file " + file1['name'] + "...\n")
        sys.stderr.flush()

    # Check whether file is public
    start = time.time()
    if fname != '-':
        f = open(fname, "wb")
    elif sys.version_info[0] > 2:
        f = sys.stdout.buffer
    else:
        f = sys.stdout
        if sys.platform in ["win32", "win64"]:
            import os
            import msvcrt
            msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)

    # Use MediaIoBaseDownload with large chunksize for better performance
    request = auth.service.files().get_media(fileId=file1['id'])

    chunksize = min(max(fileSize // 1048576 // 20 *
                        1048576, 1048576), 100 * 1048576)

    media_request = http.MediaIoBaseDownload(
        f, request, chunksize=chunksize)

    if not args.quiet:
        bar = ProgressBar(maxval=fileSize)
        bar.start()

    while True:
        try:
            download_progress, done = media_request.next_chunk()
        except errors.HttpError as error:
            if args.verbose:
                sys.stderr.write('An error occurred: %s\n' % error)
            return
        if not args.quiet:
            if download_progress:
                bar.update(int(download_progress.progress() * fileSize))
        if done:
            break

    if fname != '-':
        f.close()
    else:
        sys.stdout.flush()

    if not args.quiet:
        bar.finish()

    sz = fileSize
    elapsed = time.time() - start

    if not args.quiet:
        sys.stderr.write("Downloaded %s in %.1f seconds at %s\n" %
                         (sizeof_fmt(sz, 'B'), elapsed,
                          sizeof_fmt(sz / elapsed)))


if __name__ == "__main__":
    from pydrive.drive import GoogleDrive

    args = parse_args(description=__doc__)

    # Athenticate
    gauth = authenticate(args.config)

    # Create drive object
    drive = GoogleDrive(gauth)

    # List files and download matching files
    ls = list_files(drive,
                    parent_id=args.parent,
                    ids=args.ids,
                    patterns=args.patterns,
                    recursive=args.recursive,
                    callback=download_file,
                    callback_args=(gauth, args))

    if not ls and args.patterns and not args.quiet:
        sys.stderr.write('Not found\n')
