# Audio Converter

Fast, directory structure saving, parallel converter for audio files using `ffmpeg`

## Requirements

### OS

**Windows**, because using some windows-specific command-line notation:

* Prefixing paths with `\\?\` to disable path length limit (see `disableLengthLimit` function)
* Adding ` > NUL 2>&1` at the end of commands to disable output (see functions `isAudioFileOk` and `convertAudioFile`)

### Packages

* `argparse`
* `tqdm`

To install them, run

```bash
pip install -r requirements.txt
```

## Usage

To get info about usage, run

```
python main.py --help
```

## Example config file

[Here](default_config.json)
