#!/usr/bin/env python

"""
Download a public file from Google Drive.

This module uses the requests module to download a public file identified
by its file ID. It does not require PyDrive and Google authentication.
"""

from __future__ import print_function

import requests
import sys


def parse_args(description):
    "Parse command-line arguments"

    import argparse

    # Process command-line arguments
    parser = argparse.ArgumentParser(description=description)

    parser.add_argument('-o', '--outfile',
                        help='Output file name. If missing or is -, use stdout ' +
                        '(not recommended for large files).',
                        default="")

    parser.add_argument('-s', '--size',
                        help='Size of the file.',
                        type=int,
                        default=0)

    parser.add_argument('-k', '--chunk',
                        help='Chunk size for streaming. Default is to auto choose.',
                        type=int,
                        default=0)

    parser.add_argument('-q', '--quiet',
                        help='Suppress output.',
                        default=False,
                        action='store_true')

    parser.add_argument('-i', '--id',
                        help='Dummy tag for compatability with gd-get.',
                        action='store_true',
                        default=False)

    parser.add_argument('file_id',
                        help='ID of the file in Google Drive to be downloaded.',
                        default="")

    args = parser.parse_args()

    return args


def download_file(file_id, outfile, filesize, chunk=0, quiet=False):
    "Download file with the given file ID from Google Drive"

    URL = "https://drive.google.com/uc?export=download"

    session = requests.Session()

    response = session.get(URL, params={'id': file_id}, stream=True)

    if 'GAPS' in response.cookies.keys():
        sys.stderr.write("Error: Not a public file\n")
        sys.exit(-1)

    token = get_confirm_token(response)

    if token:
        params = {'id': file_id, 'confirm': token}
        response = session.get(URL, params=params, stream=True)

    return write_response_content(response, outfile, filesize, chunk, quiet)


def get_confirm_token(response):
    "Obtain confirmation token from response"

    for key, value in response.cookies.items():
        if key.startswith('download_warning'):
            return value

    return None


def write_response_content(response, outfile, filesize, chunk, quiet):
    """ Write the content into outfile of stdout """

    import time

    mega = 1048576
    if not chunk:
        CHUNK_SIZE = mega
    else:
        CHUNK_SIZE = chunk * mega

    bar = None
    count = 0

    if not quiet:
        try:
            from progressbar import ProgressBar, UnknownLength

            if filesize:
                bar = ProgressBar(maxval=filesize)
            else:
                bar = ProgressBar(maxval=UnknownLength)
            bar.start()

        except BaseException:
            pass

    start = time.time()
    if outfile and outfile != '-':
        f = open(outfile, "wb")
    elif sys.version_info[0] > 2:
        f = sys.stdout.buffer
    else:
        f = sys.stdout
        if sys.platform in ["win32", "win64"]:
            import os
            import msvcrt
            msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)

    for chunk in response.iter_content(CHUNK_SIZE):
        if chunk:  # filter out keep-alive new chunks
            f.write(chunk)
            count += len(chunk)

            if bar is not None:
                try:
                    bar.update(count)
                except BaseException:
                    # Size is larger than specified. Use UnknownLength
                    bar.finish()
                    bar = ProgressBar(max_value=UnknownLength)
                    bar.start()
                    bar.update(count)

    if outfile and outfile != '-':
        f.close()
    else:
        sys.stdout.flush()

    if bar is not None and (count == 0 or count == filesize):
        bar.finish()

    return count, time.time() - start


def sizeof_fmt(num, suffix='B/s'):
    for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
        if abs(num) < 1024.0:
            return "%3.1f %s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Y', suffix)


if __name__ == "__main__":
    import os
    import socket

    # Process command-line arguments
    args = parse_args(description=__doc__)

    sz, elapsed = download_file(
        args.file_id, args.outfile, args.size, args.chunk, args.quiet)

    if not args.quiet and args.size and sz != args.size:
        try:
            use_color = os.environ["LS_COLORS"] != ""
        except BaseException:
            use_color = False

        if use_color:
            sys.stderr.write("\n\033[0;31mWarning: Received " + str(sz) +
                             " bytes, but " + str(args.size) + " was expected.\033[0m")
        else:
            sys.stderr.write("\nWarning: Received " + str(sz) +
                             " bytes, but " + str(args.size) +
                             " was expected.")

    ip = requests.get('http://ip.42.pl/raw').text
    hostaddr = socket.gethostbyaddr(ip)[0]
    sys.stderr.write("Downloaded %s in %.1f seconds at %s from %s\n" %
                     (sizeof_fmt(sz, 'B'), elapsed,
                      sizeof_fmt(sz / elapsed), hostaddr))
