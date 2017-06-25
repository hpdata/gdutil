#!/usr/bin/env python

"""
Download a public file from Google Drive.

This module uses the requests package to download a public file identified
by its file ID. It does not require PyDrive and Google authentication.
It does not check the correctness of the output either.
"""

from __future__ import print_function

import sys


def parse_args(description):
    "Parse command-line arguments"

    import argparse

    # Process command-line arguments
    parser = argparse.ArgumentParser(description=description)

    parser.add_argument('-o', '--outfile',
                        help='Output file name. Use -o - for writing to stdout ' +
                        '(not recommended for large files).',
                        default="")

    parser.add_argument('-O', '--remote',
                        help='Use the remote filename as the output file name. ' +
                        'This is the default unless -o is specified.',
                        action='store_true',
                        default=True)

    parser.add_argument('-s', '--size',
                        help='Size of the file.',
                        type=int,
                        default=-1)

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
    if args.outfile:
        args.remote = False

    return args


def download_file(file_id, outfile, filesize, quiet=False):
    "Download file with the given file ID from Google Drive"
    import time
    import requests

    URL = "https://drive.google.com/uc?export=download"

    session = requests.Session()

    response = session.get(URL, params={'id': file_id}, stream=True)

    if 'GAPS' in response.cookies.keys():
        sys.stderr.write("Error: Not a public file\n")
        raise Exception

    token = get_confirm_token(response)

    if token:
        params = {'id': file_id, 'confirm': token}
    else:
        params = {'id': file_id}

    response = session.get(URL, params=params, stream=True, timeout=30)

    disposition = response.headers['Content-Disposition']
    remotefile = disposition[21:disposition.find('"', 21)]

    if args.remote:
        outfile = remotefile

    if not args.quiet:
        sys.stderr.write('Downlading %s and saving into %s ...\n' %
                         (remotefile, outfile))

    # Open file
    if outfile and outfile != '-':
        fd = open(outfile, "wb")
    elif sys.version_info[0] > 2:
        fd = sys.stdout.buffer
    else:
        fd = sys.stdout
        if sys.platform in ["win32", "win64"]:
            import os
            import msvcrt
            msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)

    if not args.quiet:
        try:
            from progressbar import ProgressBar, UnknownLength

            if filesize <= 0:
                filesize = UnknownLength

            bar = ProgressBar(maxval=filesize)
            bar.start()

        except BaseException:
            bar = None
    else:
        bar = None

    start = time.time()

    count = 0
    while True:
        try:
            count, done, bar = write_response_content(response, fd, count, bar)
            if done:
                break
            else:
                # Try to recover by continuing from where it was left
                headers = {"Range": 'bytes=%s-' % count}
                response = session.get(URL, params=params, headers=headers,
                                       stream=True, timeout=30)
        except BaseException:
            done = False
            break

    # Close file
    if outfile and outfile != '-':
        fd.close()
    else:
        sys.stdout.flush()

    elapsed = time.time() - start
    if bar and done:
        bar.finish()

    return count, elapsed


def get_confirm_token(response):
    "Obtain confirmation token from response"

    for key, value in response.cookies.items():
        if key.startswith('download_warning'):
            return value

    return None


def write_response_content(response, fd, start, bar):
    """ Write the content into outfile of stdout """

    CHUNK_SIZE = 8 * 1048576
    count = start

    try:
        for chunk in response.iter_content(CHUNK_SIZE):
            if chunk:  # filter out keep-alive new chunks
                fd.write(chunk)
                count += len(chunk)

                if bar is not None:
                    # Initial size was specified incorrectly
                    try:
                        bar.update(count)
                    except BaseException:
                        from progressbar import ProgressBar, UnknownLength
                        # Size is larger than specified. Use UnknownLength
                        bar.finish()
                        bar = ProgressBar(max_value=UnknownLength)
                        bar.start()
                        bar.update(count)
        done = True
    except requests.exceptions.ChunkedEncodingError:
        done = False

    return count, done, bar


def sizeof_fmt(num, suffix='B/s'):
    for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
        if abs(num) < 1024.0:
            return "%3.1f %s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Y', suffix)


def install_requests(verbose=False):
    """
    Install requests to a temporary directory if needed
    """

    import tempfile
    import site
    import glob
    import subprocess

    if verbose:
        sys.stderr.write('Downloading requests...')
        sys.stderr.flush()

    tmpdir = tempfile.mkdtemp()

    patterns = ['/*/*/*/site-packages',
                '/*/*/.*/*/*/site-packages',
                '/*/*/*/*/*/site-packages',
                '/*/*/*/*/*/*/site-packages',
                '/*/*/*/*/*/*/*/site-packages']
    try:
        import pip
    except:
        # Try to install pip from source
        if sys.version_info.major > 2:
            from urllib.request import urlopen
        else:
            from urllib2 import urlopen

        get_pip = tmpdir + '/get_pip.py'
        response = urlopen('https://bootstrap.pypa.io/get-pip.py')

        with open(get_pip, 'wb') as f:
            f.write(response.read())

        subprocess.call([sys.executable, get_pip,
                         '-q', '--prefix=' + tmpdir])

        # Refresh path
        for pattern in patterns:
            sit_dir = glob.glob(tmpdir + pattern)
            if sit_dir:
                site.addsitedir(sit_dir[0])
                break
        import pip

    try:
        pip.main(['install', '-q', '--user', '--root', tmpdir,
                  'requests', 'progressbar2'])
    except:
        pass

    for pattern in patterns:
        sit_dir = glob.glob(tmpdir + pattern)
        if sit_dir:
            site.addsitedir(sit_dir[0])
            break

    if verbose:
        sys.stderr.write('Done\n')
    return tmpdir


if __name__ == "__main__":
    import os
    import socket
    import shutil

    # Process command-line arguments
    args = parse_args(description=__doc__)

    try:
        import requests
        tmpdir = ""
    except:
        tmpdir = install_requests(not args.quiet)
        import requests

    try:
        sz, elapsed = download_file(
            args.file_id, args.outfile, args.size, args.quiet)
    except BaseException:
        sys.exit(-1)

    if not args.quiet and args.size > 0 and sz != args.size:
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
    try:
        hostaddr = socket.gethostbyaddr(ip)[0]
    except:
        hostaddr = ip

    sys.stderr.write("Downloaded %s in %.1f seconds at %s from %s\n" %
                     (sizeof_fmt(sz, 'B'), elapsed,
                      sizeof_fmt(sz / elapsed), hostaddr))

    if tmpdir:
        shutil.rmtree(tmpdir)
