
import getpass
import os
import shutil
from os import stat_result
from pathlib import Path, PosixPath
from unittest.mock import patch

import pytest
from gpgedit import (BACKUP_SUFFIX, TMP_DIR, TMP_FILE_NAME, File, _augment,
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
    

def test__initialize_temp():
    temp_file = Path(TMP_DIR)/TMP_FILE_NAME
    try:
        out_file = _initialize_temp(temp_file, exist_ok=True)
        assert temp_file.parent.exists()
        assert os.access(temp_file.parent, os.R_OK)
        assert os.access(temp_file.parent, os.W_OK)
        assert os.access(temp_file.parent, os.X_OK | os.W_OK)
        assert isinstance(out_file, File)
    except Exception as e:
        raise e
    finally:
        shutil.rmtree(temp_file.parent)

def test__decrypt_data_to_temp():
    original_file = File(Path(RESOURCES)/'test.txt')  
    original_file.path.write_text('test text')

    data_file = File(Path(TMP_DIR)/'test.gpg')
    data_file.mkdir(exist_ok=True)
    passwd = 'test-pswd'

    enc_dec_file = File(Path(RESOURCES)/'test-dec.txt')
    try:
        _encrypt_temp_to_data(original_file, data_file, passwd)
        _decrypt_data_to_temp(data_file, enc_dec_file, passwd)
        assert original_file.path.read_text() == enc_dec_file.path.read_text()
    except Exception as e:
        raise e
    finally:
        shutil.rmtree(data_file.path.parent)
        os.remove(original_file.path)
        if enc_dec_file.path.exists():
            os.remove(enc_dec_file.path)

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

def test__encrypt_temp_to_data():
    temp_file = File(Path(TMP_DIR)/'data-test.txt')
    temp_file.mkdir(exist_ok=True)
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
        shutil.rmtree(temp_file.path.parent)

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


def test_edit_encrypted(mocker):
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
    except Exception as e:
        raise e
    finally:
        os.remove(encrypted_file_path)
        os.remove(decrypted_file_path)
        

def test__prompt_for_path():
    pass

def test_get_input_message():
    pass

def test_generate_encrypted(mocker):
    mocker.patch('gpgedit.get_input_message', return_value='test message')
    mocker.patch('getpass.getpass', return_value='test-pswd')

    temp_dir = Path(TMP_DIR)
    try:
        test_file = Path(RESOURCES)/'test.gpg'
        generate_encrypted(test_file)
        assert test_file.exists()
        assert not temp_dir.exists()
    except Exception as e:
        raise e
    finally:
        os.remove(test_file)

# *** functions ***

def overwrite_file(file: 'File'):
    file.path.write_text(MESSAGE)

def generate_encrypted_dummy(mocker, path: Path, msg: str = 'test message', pswd: str = 'test-pswd'):
    mocker.patch('gpgedit.get_input_message', return_value=msg)
    mocker.patch('getpass.getpass', return_value=pswd)
    generate_encrypted(path)

# *** classes ***
