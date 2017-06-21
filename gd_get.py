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
                        help='Download files recursively.',
                        default=False,
                        action='store_true')

    parser.add_argument('-o', '--outfile',
                        help='Output file name. Use -o - for writing to stdout ' +
                        '(not recommended for large files).',
                        default="")

    parser.add_argument('-O', '--remote',
                        help='Use the remote filename as the output file name. ' +
                        'This is the default unless -o is specified.',
                        action='store_true',
                        default=True)

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

    parser.add_argument('-k', '--chunk',
                        help='Chunk size in megabytes. Default is to auto-choose.',
                        type=int,
                        default=0)

    parser.add_argument('-n', '--no-chksum',
                        help='Do not check the chksum of the file. Default is to check.',
                        action='store_true',
                        default=False)

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
    if args.outfile:
        args.remote = False

    return args


def md5chksum(fname):
    "Computes md5chksum of a local file"

    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def sizeof_fmt(num, suffix='B/s'):
    " Format size in human-readable format "

    for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
        if abs(num) < 1024.0:
            return "%3.1f %s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Y', suffix)


def determine_chunksize(chunk):
    " Determine proper chunk size "
    import socket
    mega = 1048576

    if chunk > 0:
        return chunk * mega, socket.gethostname()
    else:
        import requests

        ip = requests.get('http://ip.42.pl/raw').text
        try:
            hostaddr = socket.gethostbyaddr(ip)[0]
        except:
            hostaddr = ip

        if hostaddr.endswith('googleusercontent.com') or \
           hostaddr.endswith('amazonaws.com'):
            #  Use 128 MB for Google and Amazon cloud platforms
            return 128 * mega, hostaddr
        else:
            #  Use 32 MB for other platforms
            return 32 * mega, hostaddr


def download_file(file1, auth, args):
    " Download a given file "

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
        # Download file only if size is different or
        # the checksum is different Compute chksum
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
        sys.stderr.write("Downloading file " + file1['name'] + " ...\n")
        sys.stderr.flush()

    # Check whether file is public
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

    chunksize, hostaddr = determine_chunksize(args.chunk)

    start = time.time()
    media_request = http.MediaIoBaseDownload(f, request, chunksize=chunksize)

    if not args.quiet:
        bar = ProgressBar(maxval=fileSize)
        bar.start()

    sleep_interval = 0
    while True:
        try:
            download_progress, done = media_request.next_chunk()
            if sleep_interval > 0:
                time.sleep(sleep_interval)
        except errors.HttpError as error:
            sys.stderr.write('An error occurred: %s\n' % error.message)

            if error.message.find('Rate Limit Exceeded') < 0 and \
                    error.message.find('Too Many Requests') < 0:
                # Error cannot be recoverred
                return
            elif sleep_interval == 0:
                # Try to adjust chunksize based on estinated bandwidth
                # Chunksize should be able to store data for one-second
                bandwidth = (download_progress.progress() *
                             fileSize) / (time.time() - start) / 1048576

                newchunksize = chunksize
                while newchunksize < bandwidth and newchunksize < 256:
                    newchunksize *= 2

                # Chunksize should be able to store data for one second
                if newchunksize > chunksize:
                    chunksize = newchunksize

                    # Restart downloading with new chunksize
                    start = time.time()
                    media_request = http.MediaIoBaseDownload(
                        f, request, chunksize=chunksize)

                    if not args.quiet:
                        bar = ProgressBar(maxval=fileSize)
                        bar.start()

                    continue
                else:
                    # If chunksize is large enough, use exponential backoff
                    pass

            # Use exponential backoff
            if sleep_interval == 0:
                sleep_interval = 0.1
            else:
                sleep_interval *= 2
            time.sleep(sleep_interval)

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

    elapsed = time.time() - start
    sz = fileSize

    if fname != '-' and (os.path.getsize(fname) != fileSize or
                         md5chksum(fname) != file1['fileobj']['md5Checksum']):
        sys.stderr.write("Checksum of the file does not match. The file might " +
                         "be corrupted or changed during transmission.")

    if not args.quiet:
        sys.stderr.write("Downloaded %s in %.1f seconds at %s from %s\n" %
                         (sizeof_fmt(sz, 'B'), elapsed,
                          sizeof_fmt(sz / elapsed), hostaddr))

    return sz, elapsed


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
