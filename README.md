# Google Drive as High-Performance Data Archive
This module supports using Google Drive as a high-performance data archive. You can use it to authenticate with your Google account, download files using a folder ID and the file names within the folder, and upload a file using a folder ID and the local file names.

## Background
In Google Drive, each folder or file has a unique ID such as `0ByTwsK5_Tl_PemN0QVlYem11Y00` or `root`. The functions in this module identify a file using a folder ID and the file name within the folder. You can find the folder ID from the URL in Google Drive.

This module utilizes [`PyDrive`](https://pypi.python.org/pypi/PyDrive). To use the scripts `gd_list_file`, `gd_get_file`, `gd_put_file`, you must first install the PyDriver module, which you can do using the `pip` command:
```
pip install PyDrive
```

## Authenticate with Your Google Account
Before you can access your data in Google Drive, you must authenticate using your Google account that has proper permission to the folder in Google Drive. Your Google account must have read access to list or download files, and must have write access to upload files.

The authentication process requires a computer with a web browser and `python` preinstalled. The easiest way to authenticate is to download the Python script `gd_auth.py` (https://raw.githubusercontent.com/compdatasci/gdrive-archive/master/) and run it on your local computer. This scripts can automatically install a temporary copy of `PyDrive` during authentication, so you don't need to install it on your local computer.

If you use a Windows computer, please first install `Miniconda` (https://conda.io/miniconda.html) if you do not yet have Python. Then, you can run these two commands in the Windows PowerShell:
'''
curl https://raw.githubusercontent.com/compdatasci/gdrive-archive/master/gd_auth.py -outfile gd_auth.py
python gd_auth.py
'''
On Mac or Linux, which already have Python preinstalled, run the following two commands instead:
'''
curl -s -O https://raw.githubusercontent.com/compdatasci/gdrive-archive/master/gd_auth.py
python gd_auth.py
'''
After the scripts complete, you can find a file named `mycred.txt`  in your current working directory. Copy this file to a computer where you will use the module to upload or download files. Please keep this file secret to prevent others gaining unauthorized access to your account. For even stronger security, you are recommended to generate your credential for the application (see below for detail).

## List Files in Google Drive
You can list the file using the following command:
```
gd_list_files <folder_id>
```
It will list the IDs and sizes of the files in the folder. If `-p <parent_id>` is missing, the default parent folder is the `root` directory of your Google account.

### Download a List of Files
You can download a list of files using the following command:
```
gd_get_file -O -p <parent_id> <filename1> ...
```
It downloads a file in the parent folder and saves it using the given file name. The file name can also contain subdirectory names relative to the parent folder, and the path will be preserved when downloading the file.

If `-p <parent_id>` is missing, the default parent folder is the `root` directory of your Google account. If `-O` is missing, there can only be one file, which will be written to `stdout`. When you specify a list of files, the script can download up to four files concurrently.

You can also specify a local directory name using the `-d /local/path` option. For example,
```
gd_get_files -O -p <parent_id> -d /tmp <filename1> ...
```
This script will show the progress while downloading. To disable it, use the '-s' option.

### Upload a List of Files
You can upload a list of files onto Google Drive using the following command:
```
gd_put_files -p <parent_id> <filename1> ...
```
If `-p <parent_id>` is missing, the default parent folder is the root directory of your Google account. The file name can contain a relative path, which will be preserved after uploading. By default, the local path is relative to the current working directory. You can use the `-d <local_folder>` to specify a local root directory, and the path will be then relative to this folder.

When you specify a list of files, the script can upload up to four files concurrently.

Note: If a file already exists in the parent folder on Google Drive, it will be overwritten. However, Google  Drive stores older version up to 30 days.

## Create Your Own Client Secret
Google Drive's authentication process includes two separate keys: a client secret that identifies the application, and a user key that identifies the Google user. For best protection, it is recommended that you create your own client secret using the Google API Console. Please follow the following steps":
1. Go to the [Google API Console](https://console.developers.google.com/iam-admin/projects) and create your own project.
2. Search for 'Drive API', select the entry, and click 'Enable'.
3. Select 'Credentials from the left menu, click Create Credentials, select OAuth client ID.
4. Now, the product name and consent screen need to be set -> click Configure consent screen and follow the instructions. Once finished:
 a. Select Application type to "Other".
 b. Enter an appropriate name.
 c. Click Create.
5. Click Download JSON on the right side of Client ID to download `client_secret_<really long ID>.json`.

The downloaded file has all authentication information of your application. Rename the file to `client_secrets.json` and place it in your working directory and redo the authenticate step to create your `mycred.txt` file again.
