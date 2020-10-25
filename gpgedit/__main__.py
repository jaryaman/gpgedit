from gpgedit import get_input_file
from gpgedit import edit_encrypted
from gpgedit import generate_encrypted


if __name__ == '__main__':
    data_file_path = get_input_file()
    if data_file_path.exists():
        edit_encrypted(data_file_path)
    else:
        #generate_encrypted(data_file_path)
        raise NotImplementedError