# GDKit: Google Drive as High-Performance Data Repository
This module supports using Google Drive as a high-performance data repository. You can use it to download and upload files and folders between your local computer and Google Drive with multiple streams concurrently. GDkit is implemented using [`PyDrive`](https://pypi.python.org/pypi/PyDrive). It can be used as a command-line toolkit or be used as a module for Python.

## Install GDKit
GitKit requires Python, which is typically preinstalled on Mac or Linux. If you use a Windows computer with Python, we recommend `Miniconda` (https://conda.io/miniconda.html).

After installing Python, you can then install GDKit and its dependencies using the `pip` command:
```
pip install gdkit
```

**Note: This is not yet implemented. At the current development stage of GDKit, you must download GDKit manually and then install its dependencies using the `pip` command:**
```
pip install -r gdkit/requirements.txt
```

## Authenticate with Your Google Account
Before you can access your data in Google Drive, you must authenticate using a Gmail account that has proper permissions to the data repository. Read access is required to list or download files, and write access is required to upload files.

The authentication process requires you have access to a webbrowser and the command `gd-auth`:
```
gd-auth [-c /path/to/config/dir]
```
The parameter is optional. If not present, the default directory is `~/.config/gdkit`.

You can also run the authentication process on a separate computer that has Python. On Windows, you can run these two commands in the Windows PowerShell:
'''
curl https://raw.githubusercontent.com/hpdata/gdkit/master/gd_auth.py -outfile gd_auth.py
python gd_auth.py -c .
'''
On Mac or Linux, run the following two commands instead:
'''
curl -s -O https://raw.githubusercontent.com/hpdata/gdkit/master/gd_auth.py
python gd_auth.py -c .
'''
After running the commands, you will find a file named `mycred.txt` in your current working directory. Copy this file to a computer where you will use the module to upload or download files. Please keep this file secret to prevent others gaining unauthorized access to your account.

## List Files in a Google Drive Folder
You can list the file using the following command:
```
gd-ls -p <folder_id> -l
```
It will list the IDs and sizes of the specified files in the folder. If `-p <parent_id>` is not present, the default parent folder is the `root` directory of your Google account. The optional `-l` specifies the long output format.

In addition, you can also specify file names using the UNIX file-name patterns. For example, you can use the command
```
gd-ls -p <folder_id> 'data*/prefix_*.txt'
```
which would look for subfofolders whose names start with `data` in the given parent folder, and then list the files that match the patter `prefix_*.txt` in the subfolders.

### Download a List of Files
You can download a list of files using the following command:
```
gd-get -O -p <parent_id> <filename1> ...
```
It downloads a file in the parent folder and saves it using the given file name. The file name can also contain subdirectory names relative to the parent folder, and the path will be preserved when downloading the file.

If `-p <parent_id>` is missing, the default parent folder is the `root` directory of your Google account. If `-O` is missing, there can only be one file, which will be written to `stdout`. When you specify a list of files, the script can download multiple files concurrently.

You can also specify a local directory name using the `-d /local/path` option. For example,
```
gd-get -O -p <parent_id> -d /tmp <filename1> ...
```
This script shows the progress when downloading. To disable it, use the '-s' option.

### Upload a List of Files
You can upload a list of files onto Google Drive using the following command:
```
gd-put -p <parent_id> <filename1> ...
```
If `-p <parent_id>` is missing, the default parent folder is the root directory of your Google account. The file name can contain a relative path, which will be preserved after uploading. By default, the local path is relative to the current working directory. You can use the `-d <local_folder>` to specify a local root directory, and the path will be then relative to this folder.

When you specify a list of files, the script can upload up to four files concurrently.

Note: If a file already exists in the parent folder on Google Drive, it will be overwritten. However, Google  Drive stores an older version up to 30 days.

### Other Features
GDKit also supports the following commands:
- `gd-info`: list information of data repository, folder, or file
- `gd-cp`: copy files to new files or folders
- `gd-mv`: move files or folders
- `gd-ln`: link a file to another folder
- `gd-rm`: delete specified files or folders
- `gd-mkdir`: create folders recursively
- `gd-share`: controls sharing of folder and files

Use the `-h` option in the command line to see their usage.

## Tricks and Tips
### About Google Drive
Google Drive is a secure cloud storage, which you authenticate using Gmail accounts. It allows you to share data and control access for public access or individual access. In Google Drive, each folder or file has a unique ID. The root directory of your account has the ID `root`. When you share a folder with someone, you will get a folder ID such as `0ByTwsK5_Tl_PemN0QVlYem11Y00`. The commands and functions in GDKit identify files and folder using a folder ID and then the subdirectory name and file names under the folder.

### Create Your Own Client Secret
Google Drive's authentication process includes two separate keys: a client secret that identifies the application, and a user key that identifies the Google user. For best protection, it is recommended that you create your own client secret using the Google API Console. Please follow the following steps":

1. Go to the [Google API Console](https://console.developers.google.com/iam-admin/projects) and create your own project.
2. Search for 'Drive API', select the entry, and click 'Enable'.
3. Select 'Credentials' from the left menu, click 'Create Credentials', select 'OAuth client ID'.
4. Now, the product name and consent screen need to be set -> click 'Configure consent screen' and follow the instructions. Once finished:
    1. Select 'Application type' to "Other".
    2. Enter an appropriate name.
    3. Click 'Create'.
5. Click 'Download JSON' on the right side of Client ID to download `client_secret_<really long ID>.json`.

The downloaded file has all authentication information of your application. Rename the file to `client_secrets.json` and place it in your working directory and redo the authenticate step to create your `mycred.txt` file again.