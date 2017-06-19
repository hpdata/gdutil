#!/usr/bin/env python3

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
                        help='Output file name. If missing or is -, use stdout.',
                        default="")

    parser.add_argument('-sz', '--size',
                        help='Size of the file.',
                        type=int,
                        default=0)

    parser.add_argument('file_id',
                        help='ID of the file in Google Drive to be downloaded.',
                        default="")

    parser.add_argument('-q', '--quiet',
                        help='Suppress output.',
                        default=False,
                        action='store_true')

    args = parser.parse_args()

    return args


def download_file(file_id, outfile, filesize, quiet=False):
    "Download file with the given file ID from Google Drive"

    URL = "https://drive.google.com/uc?export=download"

    session = requests.Session()

    response = session.get(URL, params={'id': file_id}, stream=True)

    if len(response.cookies.items()) <= 1:
        sys.stderr.write("Invalid file ID\n")
        sys.exit(-1)

    token = get_confirm_token(response)

    if token:
        params = {'id': file_id, 'confirm': token}
        response = session.get(URL, params=params, stream=True)

    return write_response_content(response, outfile, filesize, quiet)


def get_confirm_token(response):
    "Obtain confirmation token from response"

    for key, value in response.cookies.items():
        if key.startswith('download_warning'):
            return value

    return None


def write_response_content(response, outfile, filesize, quiet):
    """ Write the content into outfile of stdout """

    import time

    CHUNK_SIZE = 1048576
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
    else:
        try:
            f = sys.stdout.buffer
        except:
            if sys.platform in ["win32", "win64"]:
                import os
                import msvcrt
                msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
            f = sys.stdout

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


def sizeof_fmt(num, suffix='Bps'):
    for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
        if abs(num) < 1024.0:
            return "%3.1f %s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Y', suffix)


if __name__ == "__main__":
    import os
    # Process command-line arguments
    args = parse_args(description=__doc__)

    sz, elapsed = download_file(
        args.file_id, args.outfile, args.size, args.quiet)

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

    sys.stderr.write("\nAverage download speed: " +
                     sizeof_fmt(sz / elapsed) + "\n")
