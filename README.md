# gpgedit

WIP: A python package for making and editing gpg-encrypted files.

## Installation
### Minimal installation (not recommended)
```
pip install git+https://github.com/jaryaman/gpgedit@master
```

### Installation to virtual environment (recommended)
```
cd ~
python -m venv gpgedit
source ~/gpgedit/bin/activate
pip install git+https://github.com/jaryaman/gpgedit@master
```
Append this alias to `~/.bashrc`
```
alias gpgedit="source ~/gpgedit/bin/activate"
```

## Usage
### With minimal installation
```bash
$ python -m gpgedit /path/to/file.gp
```

### With virtual environment
```
$ gpgedit
(gpgedit) $ python -m gpgedit /path/to/file.gp
$ deactivate
```
