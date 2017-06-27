#!/usr/bin/env python

"""
Download a list of files from Google Drive.
"""

from __future__ import print_function

import sys
import hashlib
from gd_auth import authenticate
from gd_list import list_files
import httplib2


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

    parser.add_argument('-R', '--resume',
                        help='Resume downloading the file to the specified size. ' +
                        'The output file name cannot be ''-''.',
                        action='store_true',
                        default=False)

    parser.add_argument('-c', '--config',
                        help='Configuration directory containing the ' +
                        ' credential. The default is ~/.config/gdutil/.',
                        default="")

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
    if args.resume and args.outfile == '-':
        sys.stderr('Resume downloading is not supported for stdout')
        sys.exit(-1)

    return args


def md5chksum(fname):
    "Computes md5chksum of a local file"

    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def check_lastchunk(fname, oldFileSize, service, url, blocksize=65535):
    """Check the last block of the file and return true if they are
     the same with that on Google Drive"""

    if oldFileSize < blocksize:
        blocksize = oldFileSize

    headers = {"Range": 'bytes=%s-%s' %
               (oldFileSize - blocksize, oldFileSize - 1)}
    resp, content = service._http.request(url, headers=headers)

    if resp.status == 206:
        with open(fname, 'rb') as f:
            f.seek(oldFileSize - blocksize)
            local = f.read(blocksize)

            return content == local

    return False


def sizeof_fmt(num, suffix='B/s'):
    " Format size in human-readable format "

    for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
        if abs(num) < 1024.0:
            return "%3.1f %s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Y', suffix)


def get_hostaddr():
    "Get host address for printing and determining speed"
    import requests
    import socket

    ip = requests.get('http://ip.42.pl/raw').text
    try:
        hostaddr = socket.gethostbyaddr(ip)[0]
    except:
        hostaddr = ip

    return hostaddr


def get_chunksize_perthread(hostaddr):
    " Determine the proper chunk size. "

    mega = 1048576

    if hostaddr.endswith('googleusercontent.com') or \
       hostaddr.endswith('amazonaws.com'):
        # Use 64 MB for Google and Amazon cloud platforms
        chunk = 64
    else:
        #  Use 8 MB total for other platforms
        chunk = 8

    return chunk * mega


def get_next_block(http, dld_url, headers, fileSize, chunksize, backoff):
    """
    Download the next block and update context.
    """

    import time

    for i in range(10):
        resp, content = http.request(dld_url, headers=headers)

        if backoff > 0:
            time.sleep(backoff)

        if resp.status == 206:
            # Obtained partial result successfully
            return 0, content, backoff
        elif backoff >= 2 or \
                resp.status != 429 and resp.status != 403 or \
                resp.status == 403 and \
                resp.reason.find('Rate Limit Exceeded') < 0 and \
                resp.reason.find('Too Many Requests') < 0:
            # Could not recover from error
            # Example reasons: range not satisfyable (status == 416)
            # status 429 corresponds to "Too Many Requests"
            # status 403 corresponds to some permission error

            sys.stderr.write("Error cannot be recoverred")
            break
        else:
            sys.stderr.write("Got error " + resp.reason +
                             ". Trying to recover with exponential backoff.\n")

            # Use exponential backoff
            if backoff == 0:
                backoff = 0.1
                time.sleep(backoff)
            else:
                time.sleep(backoff)
                backoff *= 2

            sys.stderr.write(
                "Increased backoff time to %.1f seconds\n" % backoff)

    return -1, '', backoff


def download_file(file1, auth, args):
    " Download a given file "

    import sys
    import os
    import time
    from progress import ResumableBar

    dirname, basename = os.path.split(file1['name'])

    if args.preserve:
        fname = args.outdir + dirname + '/' + basename
    elif args.outfile and args.outfile != '-':
        fname = args.outdir + args.outfile
    elif args.remote:
        fname = args.outdir + basename
    else:
        fname = '-'

    # If the given file is a folder, create the directory locally
    oldFileSize = 0
    fileSize = file1['fileSize']
    if fileSize < 0:
        if args.preserve and not os.path.isdir(fname):
            os.makedirs(fname)
        return

    if fname != '-' and os.path.isfile(fname):
        # Download the file only if size is different or
        # the checksum is different Compute chksum
        oldFileSize = os.path.getsize(fname)
        if oldFileSize == fileSize and \
                md5chksum(fname) == file1['fileobj']['md5Checksum']:
            # Download the file
            if not args.quiet:
                sys.stderr.write("File %s is up to date.\n" % fname)
                sys.stderr.flush()

            return
    else:
        args.resume = False
        if fname != '-' and args.preserve and \
                dirname and not os.path.isdir(dirname):
            # Create directory if not exist
            os.makedirs(dirname)

    dld_url = file1['fileobj']['downloadUrl']
    hostaddr = get_hostaddr()
    chunksize = get_chunksize_perthread(hostaddr)

    if not args.quiet:
        if args.resume:
            sys.stderr.write("Resume downloading file " +
                             file1['name'] + " ...\n")
        else:
            sys.stderr.write("Downloading file " +
                             file1['name'] + "  ...\n")
        sys.stderr.flush()

    # Open the file for appending/writing
    pstart = 0
    if fname != '-':
        if args.resume and oldFileSize > 0 and \
                check_lastchunk(fname, oldFileSize,
                                auth.service, dld_url):
            # Open file for appending
            f = open(fname, "ab")
            pstart = oldFileSize
            f.seek(pstart, 0)
        else:
            # Open file for writing
            f = open(fname, "wb")
    elif sys.version_info[0] > 2:
        f = sys.stdout.buffer
    else:
        f = sys.stdout
        if sys.platform in ["win32", "win64"]:
            import os
            import msvcrt
            msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)

    if not args.quiet:
        bar = ResumableBar(maxval=fileSize, initial_value=pstart)
        bar.start()

    # Download the file using httplib2 and URL
    interrupted = False

    # Start up
    start = time.time()
    sz = pstart   # Counter for filesize
    backoff = 0

    while True:
        try:
            pnext = sz + chunksize
            if pnext >= fileSize:
                headers = {"Range": 'bytes=%s-%s' % (sz, '')}
                pnext = fileSize
            else:
                headers = {"Range": 'bytes=%s-%s' % (sz, pnext - 1)}

            status, content, backoff = get_next_block(
                auth.service._http, dld_url, headers, fileSize, chunksize, backoff)

            if status:
                break

            f.write(content)
            sz = pnext

            if not args.quiet:
                bar.update(sz)

            if sz == fileSize:
                break

        except httplib2.ServerNotFoundError:
            sys.stderr.write("\nSite is Down\n")
            break
        except KeyboardInterrupt:
            interrupted = True
            sys.stderr.write(
                "\nDownload interrupted. You can resume it using the -R option.\n")
            break

    # Close the file and progress bar
    if fname != '-':
        f.close()
    else:
        sys.stdout.flush()
    elapsed = time.time() - start

    if not args.quiet:
        if sz == fileSize:
            bar.finish()
        else:
            sys.stderr.write('\n')

    if not args.quiet:
        sys.stderr.write("Downloaded %s in %.1f seconds at %s from %s\n" %
                         (sizeof_fmt(sz - pstart, 'B'), elapsed,
                          sizeof_fmt((sz - pstart) / elapsed), hostaddr))

    # Check the checksum of the file for integrity
    if not args.no_chksum and not interrupted and fname != '-' and sz == fileSize and \
            md5chksum(fname) != file1['fileobj']['md5Checksum']:
        sys.stderr.write("Checksum of the file does not match. The file might be corrupted " +
                         "during transmission or was changed on Google Drive during transfer.")

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
