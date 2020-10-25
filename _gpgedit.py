#!/usr/bin/python
import os
import sys
import subprocess
import getpass
import stat
import shutil
from pathlib import Path
from pathlib import PosixPath
from warnings import warn


# *** global variables ***
EDITOR = 'vim'
BACKUP_SUFFIX = '-gpgedit_backup'
TMP_DIR = '/dev/shm/gpgedit'
TMP_FILE_NAME = 'data'


# *** functions ***
def _get_input_file():
    if len(sys.argv) > 1:
        data_file = sys.argv[1]
    else:
        data_file = input("Enter file: ")
    return Path(data_file)


def _make_backup(file: 'File', backup_suffix=BACKUP_SUFFIX):
    backup_file = File(path=file.path.parent/(file.path.name + backup_suffix))
    shutil.copy(file.path, backup_file.path)
    return backup_file


def _initialize_temp(path: PosixPath):
    temp_file = File(path=path)
    temp_file.get_stats()
    temp_file.mkdir()
    os.chmod(temp_file.path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
    return temp_file


def _decrypt_data_to_temp(data_file: 'File', temp_file: 'File', passwd: str):
    cmd = "gpg -d --passphrase-fd 0 --output %s %s" % (str(temp_file.path), str(data_file.path))
    proc = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE)
    proc.stdin.write(bytes(passwd, 'utf-8'))
    proc.stdin.close()
    if proc.wait() != 0:
        raise Exception("Error decrypting file.")


def _augment(file: 'File'):
    file.get_stats()
    os.system('%s %s' % (EDITOR, str(file.path)))
    file.get_stats()

    if (file.stats[-1].st_mtime == file.stats[-2].st_mtime
            and file.stats[-1].st_size == file.stats[-2].st_size):
        raise Exception("Data unchanged; not writing encrypted file.")


def _encrypt_temp_to_data(temp_file: 'File', data_file: 'File', passwd: str):
    cmd = "gpg -a --yes --symmetric --passphrase-fd 0 --output %s %s" % (str(data_file.path), str(temp_file.path))
    proc = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE)
    proc.stdin.write(bytes(passwd, 'utf-8'))
    proc.stdin.close()
    if proc.wait() != 0:
        raise Exception("Error encrypting file.")


def _file_changed(file: 'File'):
    file.get_stats()
    return (file.stats[-1].st_mtime != file.stats[-2].st_mtime
            or file.stats[-1].st_size != file.stats[-2].st_size)


def edit():
    data_file_path = _get_input_file()
    data_file = File(path=data_file_path)
    data_file.get_stats()

    backup_file = _make_backup(data_file)
    temp_file = _initialize_temp(Path(TMP_DIR)/TMP_FILE_NAME)

    try:
        passwd = getpass.getpass()
        _decrypt_data_to_temp(data_file, temp_file, passwd)
        _augment(temp_file)
        _encrypt_temp_to_data(temp_file, data_file, passwd)
    except Exception as e:
        if _file_changed(data_file):
            shutil.copy(backup_file.path, data_file.path)
            warn("Restored encrypted file from backup.", UserWarning)
        raise e
    finally:
        shutil.rmtree(temp_file.path.parent)
        os.remove(backup_file.path)


def _prompt_for_path():
    path = input('Enter path (default .):')
    if len(path) == 0:
        return '.'
    else:
        return path


def generate():
    path = _prompt_for_path()
    msg = input('Message:')

    passwd = getpass.getpass()
    cmd = f'echo {msg} | gpg - a - c > {path}'
    proc = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE)
    proc.stdin.write(bytes(passwd, 'utf-8'))
    proc.stdin.close()


# *** classes ***
class File:
    def __init__(self, path: PosixPath):
        self.path = path
        self.stats = []

    def get_stats(self):
        self.stats.append(os.stat(self.path))

    def mkdir(self, exist_ok=False):
        parent = self.path.parent
        parent.mkdir(exist_ok=exist_ok)


if __name__ == '__main__':
    generate()
    edit()
