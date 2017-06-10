#!/usr/bin/env python

"""
Authenticate for Google Drive access.
"""

import sys


def install_pydrive(verbose=False):
    """
    Install Pydrive to a temporary directory
    """

    import tempfile
    import site
    import glob
    import subprocess
    import os

    tmpdir = tempfile.mkdtemp()

    if verbose:
        sys.stdout.write('pydrive is missing. Temporily installing it...')
        sys.stdout.flush()

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

        with open(get_pip, 'w') as f:
            f.write(response.read())

        subprocess.call([sys.executable, get_pip,
                         '-q', '--prefix=' + tmpdir])

        # Refresh path
        sit_dir = glob.glob(tmpdir + '/*/*/site-packages')
        site.addsitedir(sit_dir[0])
        os.environ["PYTHONPATH"] = sit_dir[0]
        import pip

    # Install pydrive and related packages
    pip.main(['install', '-q', '--user', '--root', tmpdir, 'six',
              'httplib2', 'uritemplate', 'pyasn1', 'pyasn1-modules',
              'rsa', 'oauth2client'])
    try:
        pip.main(['install', '-q', '--user', '--root', tmpdir, 'pydrive'])
    except:
        pass

    for pattern in ['/*/*/*/site-packages',
                    '/*/*/.*/*/*/site-packages',
                    '/*/*/*/*/*/site-packages']:
        sit_dir = glob.glob(tmpdir + pattern)
        if sit_dir:
            site.addsitedir(sit_dir[0])
            break

    if verbose:
        print('Done')

    return tmpdir


def authenticate(src_dir, cmdline=False, verbose=False):
    """"
    Authenticate using web browser and cache the credential.
    """

    from pydrive.auth import GoogleAuth
    import os.path

    # Authenticate Google account
    gauth = GoogleAuth()
    gauth.settings['client_config_file'] = src_dir + '/' + \
        'client_secrets.json'

    if not os.path.exists(src_dir + "/client_secrets.json"):
        with open('client_secrets.json', 'w') as f:
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

    credfile = 'mycred.txt'

    try:
        # Try to load saved client credentials
        if os.path.exists(src_dir + "/" + credfile):
            gauth.LoadCredentialsFile(src_dir + "/" + credfile)

        if gauth.credentials is None:
            raise Exception('Empty credential')
        elif gauth.access_token_expired:
            # Refresh them if expired
            gauth.Refresh()
            # Save the current credentials to a file
            gauth.SaveCredentialsFile(src_dir + "/" + credfile)

            if verbose:
                print('Refreshed the credential.')
        else:
            # Initialize the saved creds
            gauth.Authorize()
            if verbose:
                print('Credential ' + src_dir + "/" +
                      credfile + ' is up to date.')

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
            gauth.SaveCredentialsFile(src_dir + "/" + credfile)

            if verbose:
                print('Credential saved to ' + src_dir + "/" + credfile)
        except KeyboardInterrupt:
            return None

    return gauth


if __name__ == "__main__":
    import argparse
    import shutil

    # Process command-line arguments
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument('-d', '--dir',
                        help='Directory containing credential. ' +
                        'The default is current directory',
                        default=".")

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
    gauth = authenticate(args.dir, args.no_browser, not args.quiet)

    if tmpdir:
        shutil.rmtree(tmpdir)
