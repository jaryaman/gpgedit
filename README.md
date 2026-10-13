# gpgedit

![Python package](https://github.com/jaryaman/gpgedit/workflows/Python%20package/badge.svg)

A python package for making and editing gpg-encrypted files on Linux.

## Installation
Requires [uv](https://docs.astral.sh/uv/getting-started/installation/), `gpg` and `vim`.

```
$ uv tool install git+https://github.com/jaryaman/gpgedit@master
```

## Usage
```bash
$ gpgedit /path/to/file.gpg
```
If the file exists it is decrypted to RAM and opened in vim; otherwise you are prompted for its contents and a new encrypted file is made.

## Development
```
$ git clone https://github.com/jaryaman/gpgedit
$ cd gpgedit
$ uv sync
$ uv run pytest
```
