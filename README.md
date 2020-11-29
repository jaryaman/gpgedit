# gpgedit

https://github.com/jaryaman/gpgedit/workflows/python-package/badge.svg

A python package for making and editing gpg-encrypted files on Linux.

## Installation
### Minimal installation (not recommended)
```
$ pip install git+https://github.com/jaryaman/gpgedit@master
```

### Installation to virtual environment (recommended)
Assuming you have venv installed (if not [see here](https://packaging.python.org/guides/installing-using-pip-and-virtual-environments/))

```
$ cd ~
$ python -m venv gpgedit
$ source ~/gpgedit/bin/activate
(gpgedit) $ pip install wheel
(gpgedit) $ pip install git+https://github.com/jaryaman/gpgedit@master
(gpgedit) $ deactivate
$
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
(gpgedit) $ deactivate
$ 
```
