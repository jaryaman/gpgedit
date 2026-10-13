from gpgedit import get_input_file
from gpgedit import edit_encrypted
from gpgedit import generate_encrypted
from gpgedit import install_signal_handlers


def main():
    install_signal_handlers()
    data_file_path = get_input_file()
    if data_file_path.exists():
        edit_encrypted(data_file_path)
    else:
        generate_encrypted(data_file_path)


if __name__ == '__main__':
    main()
