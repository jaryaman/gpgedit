# gpgedit

![Python package](https://github.com/jaryaman/gpgedit/workflows/Python%20package/badge.svg)

A python package for making and editing gpg-encrypted files on Linux.

## Installation
Requires [uv](https://docs.astral.sh/uv/getting-started/installation/), `gpg` and `vim`.

```
uv tool install git+https://github.com/jaryaman/gpgedit@master
```

## Usage
```bash
gpgedit /path/to/file.gpg
```
If the file exists it is decrypted to RAM and opened in vim; otherwise you are prompted for its contents and a new encrypted file is made.

### Changing the password of existing files
```bash
gpgedit --rekey file1.gpg file2.gpg file3.gpg
```
You are asked for the old password once, so the files must all share it, and then for the new password twice.
Each file is decrypted in memory, re-encrypted, and checked before the original is replaced.
If any file cannot be decrypted, none of them are changed.

## Development
```
git clone https://github.com/jaryaman/gpgedit
cd gpgedit
uv sync
uv run pytest
```
