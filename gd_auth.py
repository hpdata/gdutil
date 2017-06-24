#!/usr/bin/env python

"""
Authenticate for Google Drive access.
"""

import sys


def authenticate(conf_dir, cmdline=False, verbose=False):
    """"
    Authenticate using web browser and save the credential into specified
    directory. If directory is not specified, the default is ~/.config/gdutil/.
    """

    from pydrive.auth import GoogleAuth
    import os
    import os.path
    from httplib2 import Http

    # Authenticate Google account and intialize caching
    gauth = GoogleAuth()
    gauth.http = Http(cache=os.path.expanduser('~') + '/.cache/gdutil')

    if not conf_dir:
        conf_dir = os.path.expanduser('~') + '/.config/gdutil'
        if not os.path.exists(conf_dir):
            os.makedirs(conf_dir, 0o700)

        if os.path.exists("./mycred.txt"):
            credfile = './mycred.txt'
        else:
            credfile = conf_dir + '/mycred.txt'
    else:
        credfile = conf_dir + '/mycred.txt'

    clientfile = conf_dir + '/' + 'client_secrets.json'
    gauth.settings['client_config_file'] = clientfile

    if not os.path.exists(clientfile):
        with open(clientfile, 'w') as f:
            f.write('{"installed":{"client_id":' +
                    '"493620386912-06j6iof499pgi2r3dtkumesmv61qj8p8' +
                    '.apps.googleusercontent.com",' +
                    '"project_id":"docker-data-volumes",' +
                    '"auth_uri":"https://accounts.google.com/o/oauth2/auth",' +
                    '"token_uri":"https://accounts.google.com/o/oauth2/' +
                    'token","auth_provider_x509_cert_url":' +
                    '"https://www.googleapis.com/oauth2/v1/certs",' +
                    '"client_secret":"V4j_VTyGN5oN7TpWv89qhPtY",' +
                    '"redirect_uris":' +
                    '["urn:ietf:wg:oauth:2.0:oob","http://localhost"]}}')

    try:
        # Try to load saved client credentials
        if os.path.exists(credfile):
            gauth.LoadCredentialsFile(credfile)

        if gauth.credentials is None:
            raise Exception('Empty credential')
        elif gauth.access_token_expired:
            # Refresh them if expired
            gauth.Refresh()
            # Save the current credentials to a file
            gauth.SaveCredentialsFile(credfile)

            if verbose:
                print('Refreshed the credential.')
        else:
            # Initialize the saved creds
            gauth.Authorize()
            if verbose:
                print('Credential ' + credfile + ' is up to date.')

    except:
        if verbose:
            print('*** You need to authenticate using your Google account.')
            print('*** This needs to be done only once.')

        try:
            if cmdline:
                gauth.CommandLineAuth()
            else:
                # Authenticate if the credential does not exist
                gauth.LocalWebserverAuth()

            # Save the current credentials to a file
            gauth.SaveCredentialsFile(credfile)

            if verbose:
                print('Credential saved to ' + credfile)
        except KeyboardInterrupt:
            return None

    return gauth


def install_pydrive(verbose=False):
    """
    Install PyDrive to a temporary directory if needed
    """

    import tempfile
    import site
    import glob
    import subprocess

    tmpdir = tempfile.mkdtemp()

    if verbose:
        sys.stderr.write('Downloading PyDrive...')
        sys.stderr.flush()

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

    # Install pydrive and related packages
    pip.main(['install', '-q', '--user', '--root', tmpdir, 'six',
              'httplib2', 'uritemplate', 'pyasn1', 'pyasn1-modules',
              'rsa', 'oauth2client'])
    try:
        pip.main(['install', '-q', '--user', '--root', tmpdir, 'PyDrive'])
    except:
        pass

    for pattern in patterns:
        sit_dir = glob.glob(tmpdir + pattern)
        if sit_dir:
            site.addsitedir(sit_dir[0])
            break

    if verbose:
        print('Done')

    return tmpdir


if __name__ == "__main__":
    import argparse
    import shutil

    # Process command-line arguments
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument('-c', '--config',
                        help='Configuration directory containing the ' +
                        ' credential. The default is ~/.config/gdutil/.',
                        default="")

    parser.add_argument('-n', '--no-browser',
                        help='Do not use browser but command-line.',
                        action='store_true',
                        default=False)

    parser.add_argument('-q', '--quiet',
                        help='Silient all screen output.',
                        action='store_true',
                        default=False)

    args = parser.parse_args()

    try:
        __import__('pydrive.auth')
        tmpdir = ""
    except:
        tmpdir = install_pydrive(not args.quiet)

    # Athenticate
    gauth = authenticate(args.config, args.no_browser, not args.quiet)

    if tmpdir:
        shutil.rmtree(tmpdir)
