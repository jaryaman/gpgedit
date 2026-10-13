
import getpass
import os
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
from os import stat_result
from pathlib import Path, PosixPath
from unittest.mock import patch

import pytest
from gpgedit import (BACKUP_SUFFIX, TMP_FILE_NAME, File, _augment,
                     _decrypt_data_to_temp, _encrypt_temp_to_data,
                     _file_changed, _initialize_temp, _launch_editor,
                     _make_backup, edit_encrypted, generate_encrypted,
                     get_input_file, get_input_message)

# *** global variables ***
TEST_FILE = 'test.gpg'
RESOURCES = './resources'
MESSAGE = '***Hello world!***'


# *** functions ***
def make_file_struct(name: str = TEST_FILE):
    path = Path(name)
    out_file = File(path)
    return out_file

def write_msg_to_file(name: str = TEST_FILE, msg = 'test'):
    file_struct = make_file_struct(name)
    with file_struct.path.open(mode = 'w') as f:
        f.write(msg)
    return file_struct

def write_script(path: Path, body: str):
    path.write_text('#!/bin/sh\n' + body + '\n')
    path.chmod(stat.S_IRWXU)
    return path


# *** fixtures ***
@pytest.fixture
def shm_root(mocker):
    root = Path(tempfile.mkdtemp(prefix='gpgedit-test-', dir='/dev/shm'))
    mocker.patch('gpgedit.TMP_ROOT', str(root))
    yield root
    shutil.rmtree(root)


# *** tests for classes ***
def test_init_file_object():
    test_file = make_file_struct(TEST_FILE)
    assert isinstance(test_file.path, PosixPath)


def test_make_file_struct_struct_stats():
    test_file = make_file_struct(TEST_FILE)
    with test_file.path.open('w') as f:
        f.write('test')
    try:
        test_file.get_stats()
        assert isinstance(test_file.stats[0], os.stat_result)
    except Exception as e:
        raise e
    finally:
        os.remove(test_file.path)


def test_file_mkdir():
    path_to_file = './test/test-deep/test.gpg'
    posix_path_to_file = Path(path_to_file)
    assert not posix_path_to_file.parent.exists()
    test_file = make_file_struct(path_to_file)
    try:
        test_file.mkdir(exist_ok=False)
        assert test_file.path.parent.exists()
    except Exception as e:
        raise e
    finally:
        shutil.rmtree(test_file.path.parent)
        assert not posix_path_to_file.parent.exists()


# *** tests for functions ***
def test_get_input_file():
    # TODO: Not sure how to test this!
    pass


def test__make_backup():
    test_file = write_msg_to_file(name=TEST_FILE, msg='test')            
    backup_file = _make_backup(test_file, backup_suffix=BACKUP_SUFFIX)
    assert test_file.path.name+BACKUP_SUFFIX == backup_file.path.name
    assert backup_file.path.exists()
    os.remove(backup_file.path)
    assert not backup_file.path.exists()
    

def test__initialize_temp(shm_root):
    out_file = _initialize_temp(shm_root)
    assert isinstance(out_file, File)
    assert out_file.path.name == TMP_FILE_NAME
    assert out_file.path.parent.parent == shm_root
    assert stat.S_IMODE(os.stat(out_file.path.parent).st_mode) == 0o700

def test__initialize_temp_gives_each_session_its_own_directory(shm_root):
    first = _initialize_temp(shm_root)
    second = _initialize_temp(shm_root)
    assert first.path.parent != second.path.parent

def test__initialize_temp_refuses_disk_backed_root():
    resources = Path(RESOURCES)
    before = sorted(resources.iterdir())
    with pytest.raises(Exception, match='RAM'):
        _initialize_temp(resources)
    assert sorted(resources.iterdir()) == before

def test__decrypt_data_to_temp(shm_root):
    original_file = File(Path(RESOURCES)/'test.txt')  
    original_file.path.write_text('test text')

    data_file = File(shm_root/'test.gpg')
    passwd = 'test-pswd'

    enc_dec_file = File(Path(RESOURCES)/'test-dec.txt')
    try:
        _encrypt_temp_to_data(original_file, data_file, passwd)
        _decrypt_data_to_temp(data_file, enc_dec_file, passwd)
        assert original_file.path.read_text() == enc_dec_file.path.read_text()
    except Exception as e:
        raise e
    finally:
        os.remove(original_file.path)
        if enc_dec_file.path.exists():
            os.remove(enc_dec_file.path)

@pytest.mark.parametrize('name', ['with space.gpg', '$(touch pwned).gpg', 'a;touch pwned;.gpg'])
def test_encrypt_decrypt_treats_path_as_literal(shm_root, name):
    plain_file = File(shm_root/'plain.txt')
    plain_file.path.write_text('test text')
    data_file = File(Path(RESOURCES)/name)
    dec_file = File(shm_root/('dec ' + name))
    passwd = 'test-pswd'
    try:
        _encrypt_temp_to_data(plain_file, data_file, passwd)
        _decrypt_data_to_temp(data_file, dec_file, passwd)
        assert dec_file.path.read_text() == 'test text'
        assert not Path('pwned').exists()
    finally:
        for leftover in (data_file.path, Path('pwned')):
            if leftover.exists():
                os.remove(leftover)

@pytest.mark.skipif(shutil.which('vim') is None, reason='needs vim')
def test__launch_editor_leaves_no_trace_in_home(mocker, tmp_path):
    home = tmp_path/'home'
    home.mkdir()
    work = tmp_path/'work'
    work.mkdir()
    test_file = File(work/'data')
    test_file.path.write_text('secret\n')
    # drive real vim non-interactively: yank and paste the line, then save
    wrapper = write_script(tmp_path/'editor', 
        'HOME=%s exec vim --not-a-term "$@" -c "normal yyp" -c wq </dev/null >/dev/null 2>&1' % home)
    mocker.patch('gpgedit.EDITOR', str(wrapper))

    _launch_editor(test_file)

    assert test_file.path.read_text() == 'secret\nsecret\n'
    assert list(home.iterdir()) == []
    assert list(work.iterdir()) == [test_file.path]

def test__launch_editor():
    # Not sure how to test this!
    pass

def test__augment_with_no_change(mocker):
    mocker.patch('gpgedit._launch_editor')

    test_file = File(Path(RESOURCES)/'test.txt')
    test_file.path.write_text('test text\n')
    with pytest.raises(Exception) as _:
        _augment(test_file)    

def test__augment_with_change(mocker):
    test_file = File(Path(RESOURCES)/'test.txt')
    original_message = 'test text\n'
    test_file.path.write_text(original_message)
    mocker.patch('gpgedit._launch_editor', new=overwrite_file)

    try:
        _augment(test_file)
        assert test_file.path.read_text() != original_message
    except Exception as e:
        raise e
    finally:
        if test_file.path.exists():
            os.remove(test_file.path)

def test__encrypt_temp_to_data(shm_root):
    temp_file = File(shm_root/'data-test.txt')
    temp_file.path.write_text('test text')

    data_file = File(Path(RESOURCES)/'test.gpg')
    passwd = 'test-pswd'
    try:
        _encrypt_temp_to_data(temp_file, data_file, passwd)
        assert temp_file.path.exists()
    except Exception as e:
        raise e
    finally:
        if data_file.path.exists():
            os.remove(data_file.path)

def test__file_changed():
    test_file = File(Path(RESOURCES)/'test.txt')
    original_message = 'test text\n'
    test_file.path.write_text(original_message)
    test_file.get_stats()
    
    try:
        assert not _file_changed(test_file)
        test_file.path.write_text('new message')
        assert _file_changed(test_file)
        assert not _file_changed(test_file)
    except Exception as e:
        raise e
    finally:
        os.remove(test_file.path)


def test_edit_encrypted(mocker, shm_root):
    encrypted_file_path = Path(RESOURCES)/'test.gpg'
    decrypted_file_path = Path(RESOURCES)/'decrypted.txt'
    pswd = 'test-pass'
    msg_original = 'this is a test'

    generate_encrypted_dummy(mocker, encrypted_file_path, pswd=pswd, msg=msg_original)
    
    mocker.patch('getpass.getpass', return_value=pswd)
    mocker.patch('gpgedit._augment', new=overwrite_file)
    
    try:
        edit_encrypted(encrypted_file_path)
        _decrypt_data_to_temp(File(encrypted_file_path), File(decrypted_file_path), pswd)
        assert decrypted_file_path.read_text() == MESSAGE
        assert list(shm_root.iterdir()) == []
    except Exception as e:
        raise e
    finally:
        os.remove(encrypted_file_path)
        os.remove(decrypted_file_path)

def test_edit_encrypted_cleans_up_when_temp_cannot_be_created(mocker, shm_root):
    encrypted_file_path = Path(RESOURCES)/'test.gpg'
    backup_file_path = Path(RESOURCES)/('test.gpg' + BACKUP_SUFFIX)
    generate_encrypted_dummy(mocker, encrypted_file_path)
    original = encrypted_file_path.read_bytes()
    mocker.patch('gpgedit.TMP_ROOT', RESOURCES)  # on disk, so refused

    try:
        with pytest.raises(Exception, match='RAM'):
            edit_encrypted(encrypted_file_path)
        assert not backup_file_path.exists()
        assert encrypted_file_path.read_bytes() == original
    finally:
        for leftover in (encrypted_file_path, backup_file_path):
            if leftover.exists():
                os.remove(leftover)

@pytest.mark.parametrize('signum', [signal.SIGTERM, signal.SIGHUP])
def test_edit_encrypted_removes_plaintext_when_signalled(mocker, shm_root, tmp_path, signum):
    encrypted_file_path = Path(RESOURCES)/'test.gpg'
    backup_file_path = Path(RESOURCES)/('test.gpg' + BACKUP_SUFFIX)
    decrypted_file_path = shm_root/'decrypted.txt'
    pswd = 'test-pass'
    generate_encrypted_dummy(mocker, encrypted_file_path, pswd=pswd, msg='this is a test')
    editor = write_script(tmp_path/'editor', 'exec sleep 30')
    session = (
        "import getpass, sys\n"
        "from pathlib import Path\n"
        "import gpgedit\n"
        "gpgedit.TMP_ROOT, gpgedit.EDITOR = sys.argv[1], sys.argv[2]\n"
        "getpass.getpass = lambda *args, **kwargs: sys.argv[4]\n"
        "gpgedit.install_signal_handlers()\n"
        "gpgedit.edit_encrypted(Path(sys.argv[3]))\n"
    )

    proc = subprocess.Popen([sys.executable, '-c', session, str(shm_root), str(editor),
                             str(encrypted_file_path), pswd])
    try:
        deadline = time.time() + 20
        while not list(shm_root.glob('*/' + TMP_FILE_NAME)):
            assert proc.poll() is None, 'session exited before reaching the editor'
            assert time.time() < deadline, 'session never decrypted to temp'
            time.sleep(0.05)
        assert list(shm_root.glob('*/' + TMP_FILE_NAME))[0].read_text() == 'this is a test\n'

        proc.send_signal(signum)
        assert proc.wait(timeout=20) != 0

        assert list(shm_root.iterdir()) == []
        assert not backup_file_path.exists()
        _decrypt_data_to_temp(File(encrypted_file_path), File(decrypted_file_path), pswd)
        assert decrypted_file_path.read_text() == 'this is a test\n'
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
        for leftover in (encrypted_file_path, backup_file_path):
            if leftover.exists():
                os.remove(leftover)


def test__prompt_for_path():
    pass

def test_get_input_message_does_not_echo(mocker):
    mocker.patch('builtins.input', side_effect=AssertionError('message was read with echo'))
    mocker.patch('getpass.getpass', return_value='hunter2')
    assert get_input_message() == 'hunter2'

def test_generate_encrypted(mocker, shm_root):
    mocker.patch('gpgedit.get_input_message', return_value='test message')
    mocker.patch('getpass.getpass', return_value='test-pswd')
    decrypted_file_path = shm_root/'decrypted.txt'

    try:
        test_file = Path(RESOURCES)/'test.gpg'
        generate_encrypted(test_file)
        assert test_file.exists()
        assert list(shm_root.iterdir()) == []
        _decrypt_data_to_temp(File(test_file), File(decrypted_file_path), 'test-pswd')
        assert decrypted_file_path.read_text() == 'test message\n'
    except Exception as e:
        raise e
    finally:
        os.remove(test_file)

def test_generate_encrypted_rejects_mistyped_passphrase(mocker, shm_root):
    mocker.patch('gpgedit.get_input_message', return_value='test message')
    mocker.patch('getpass.getpass', side_effect=['test-pswd', 'test-pswf'])
    test_file = Path(RESOURCES)/'test.gpg'

    try:
        with pytest.raises(Exception, match='do not match'):
            generate_encrypted(test_file)
        assert not test_file.exists()
        assert list(shm_root.iterdir()) == []
    finally:
        if test_file.exists():
            os.remove(test_file)

# *** functions ***

def overwrite_file(file: 'File'):
    file.path.write_text(MESSAGE)

def generate_encrypted_dummy(mocker, path: Path, msg: str = 'test message', pswd: str = 'test-pswd'):
    mocker.patch('gpgedit.get_input_message', return_value=msg)
    mocker.patch('getpass.getpass', return_value=pswd)
    generate_encrypted(path)

# *** classes ***
