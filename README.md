# Iridium CLI

A command-line interface for communicating with the Iridium network.

## Usage

```sh
iridium-cli [OPTIONS] COMMAND [ARGS]...
```

### Options
```sh
--help  Show this message and exit.
```

### Commands
```sh
send
    -m  [MESSAGE]
    -f  [FILENAME]
```

## Structure

- _main.py_: Primary file that contains the methods for the CLI.
- _credentials.json.gpg_: GPG decrypt this file to _credentials.json_.
    Contains secrets for the Gmail API and the Iridium IMEI.
    
## Installation

Install all dependencies and the CLI using `pipenv`:
```sh
pipenv install
```
Alternatively, install system-wide using `pip3`:
```sh
pip3 install -r requirements.txt
``` 