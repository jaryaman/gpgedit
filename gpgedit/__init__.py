#!/usr/bin/python
import getpass
import os
import shutil
import signal
import subprocess
import sys
import tempfile
from pathlib import Path, PosixPath
from warnings import warn

# *** global variables ***
EDITOR = 'vim'
# no swap file, no viminfo, no undo/backup files: nothing vim writes may outlive the session
EDITOR_ARGS = ['-n', '-i', 'NONE', '-c', 'set noundofile nobackup nowritebackup']
BACKUP_SUFFIX = '-gpgedit_backup'
TMP_ROOT = '/dev/shm'
TMP_DIR_PREFIX = 'gpgedit-'
TMP_FILE_NAME = 'data'
RAM_FILESYSTEMS = ('tmpfs', 'ramfs')


# *** functions ***
def get_input_file():
    if len(sys.argv) > 1:
        data_file = sys.argv[1]
    else:
        data_file = input("Enter file: ")
    return Path(data_file)


def _make_backup(file: 'File', backup_suffix=BACKUP_SUFFIX):
    backup_file = File(path=file.path.parent/(file.path.name + backup_suffix))
    shutil.copy(file.path, backup_file.path)
    return backup_file


def _filesystem_type(path: PosixPath):
    path = path.resolve()
    fs_type, longest = None, -1
    with open('/proc/mounts') as mounts:
        for line in mounts:
            _, mount_point, mount_type = line.split()[:3]
            # /proc/mounts octal-escapes whitespace in mount points
            mount_point = Path(mount_point.encode().decode('unicode_escape'))
            if mount_point == path or mount_point in path.parents:
                # on a tie the later mount shadows the earlier one
                if len(mount_point.parts) >= longest:
                    fs_type, longest = mount_type, len(mount_point.parts)
    return fs_type


def _initialize_temp(root: PosixPath):
    fs_type = _filesystem_type(root)
    if fs_type not in RAM_FILESYSTEMS:
        raise Exception("%s is not RAM-backed (%s); refusing to decrypt there." % (root, fs_type))
    # mkdtemp creates the directory readable, writable and searchable only by us
    temp_dir = tempfile.mkdtemp(prefix=TMP_DIR_PREFIX, dir=str(root))
    return File(path=Path(temp_dir)/TMP_FILE_NAME)


def _remove_temp(temp_file: 'File'):
    if temp_file is not None:
        shutil.rmtree(temp_file.path.parent)


def _raise_on_signal(signum, frame):
    sys.exit(128 + signum)


def install_signal_handlers():
    # turn a closed terminal or a kill into an exception, so the finally blocks remove the plaintext
    for signum in (signal.SIGHUP, signal.SIGTERM):
        signal.signal(signum, _raise_on_signal)


def _decrypt_data_to_temp(data_file: 'File', temp_file: 'File', passwd: str):
    cmd = ['gpg', '-d', '--batch', '--no-tty', '--passphrase-fd', '0',
           '--output', str(temp_file.path), '--', str(data_file.path)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    proc.stdin.write(bytes(passwd, 'utf-8'))
    proc.stdin.close()
    if proc.wait() != 0:
        raise Exception("Error decrypting file.")

def _launch_editor(file: 'File'):
    subprocess.call([EDITOR] + EDITOR_ARGS + [str(file.path)])

def _augment(file: 'File'):
    file.get_stats()
    _launch_editor(file)
    file.get_stats()

    if (file.stats[-1].st_mtime == file.stats[-2].st_mtime
            and file.stats[-1].st_size == file.stats[-2].st_size):
        raise Exception("Data unchanged; not writing encrypted file.")


def _encrypt_temp_to_data(temp_file: 'File', data_file: 'File', passwd: str):
    cmd = ['gpg', '-a', '--yes', '--batch', '--no-tty', '--symmetric', '--passphrase-fd', '0',
           '--output', str(data_file.path), '--', str(temp_file.path)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    proc.stdin.write(bytes(passwd, 'utf-8'))
    proc.stdin.close()
    if proc.wait() != 0:
        raise Exception("Error encrypting file.")


def _file_changed(file: 'File'):
    file.get_stats()
    return (file.stats[-1].st_mtime != file.stats[-2].st_mtime
            or file.stats[-1].st_size != file.stats[-2].st_size)


def edit_encrypted(data_file_path: PosixPath):
    data_file = File(path=data_file_path)
    data_file.get_stats()

    backup_file = _make_backup(data_file)
    temp_file = None

    try:
        temp_file = _initialize_temp(Path(TMP_ROOT))
        passwd = getpass.getpass()
        _decrypt_data_to_temp(data_file, temp_file, passwd)
        _augment(temp_file)
        _encrypt_temp_to_data(temp_file, data_file, passwd)
    except BaseException as e:  # also a signal or Ctrl-C arriving mid-encryption
        if _file_changed(data_file):
            shutil.copy(backup_file.path, data_file.path)
            warn("Restored encrypted file from backup.", UserWarning)
        raise e
    finally:
        _remove_temp(temp_file)
        os.remove(backup_file.path)


def _prompt_for_path():
    path = input('Enter path (default .):')
    if len(path) == 0:
        return '.'
    else:
        return path

def get_input_message():
    return getpass.getpass('Message:')


def _get_new_passphrase():
    passwd = getpass.getpass()
    if getpass.getpass('Repeat password: ') != passwd:
        raise Exception("Passwords do not match.")
    return passwd

def generate_encrypted(data_file_path: PosixPath):
    if not data_file_path.parent.exists():
        data_file_path.parent.mkdir(exist_ok=True)
    
    data_file = File(data_file_path)
    msg = get_input_message()
    msg += '\n'
    passwd = _get_new_passphrase()
    temp_file = None

    try:
        temp_file = _initialize_temp(Path(TMP_ROOT))
        with temp_file.path.open(mode='w') as f:
            f.write(msg)
        _encrypt_temp_to_data(temp_file, data_file, passwd)
    except Exception as e:
        raise e
    finally:
        _remove_temp(temp_file)


# *** classes ***
class File:
    def __init__(self, path: PosixPath):
        self.path = path
        self.stats = []

    def get_stats(self):
        self.stats.append(os.stat(self.path))

    def mkdir(self, exist_ok=False, parents=False):
        parent = self.path.parent
        parent.mkdir(exist_ok=exist_ok, parents=parents)
