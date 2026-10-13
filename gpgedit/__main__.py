import argparse
from pathlib import Path

from gpgedit import get_input_file
from gpgedit import edit_encrypted
from gpgedit import generate_encrypted
from gpgedit import install_signal_handlers
from gpgedit import rekey


def main(argv=None):
    parser = argparse.ArgumentParser(prog='gpgedit', description='Make and edit gpg-encrypted files.')
    parser.add_argument('files', nargs='*', type=Path, metavar='FILE')
    parser.add_argument('--rekey', action='store_true',
                        help='re-encrypt the given files, which share one password, under a new password')
    parser.add_argument('--allow-legacy', action='store_true',
                        help='with --rekey, also accept old files that have no integrity protection')
    args = parser.parse_args(argv)
    if args.rekey and not args.files:
        parser.error('--rekey needs at least one file')
    if args.allow_legacy and not args.rekey:
        parser.error('--allow-legacy only applies to --rekey')
    if not args.rekey and len(args.files) > 1:
        parser.error('give one file to edit, or use --rekey for several')

    install_signal_handlers()
    if args.rekey:
        rekey(args.files, allow_legacy=args.allow_legacy)
        return
    data_file_path = args.files[0] if args.files else get_input_file()
    if data_file_path.exists():
        edit_encrypted(data_file_path)
    else:
        generate_encrypted(data_file_path)


if __name__ == '__main__':
    main()
