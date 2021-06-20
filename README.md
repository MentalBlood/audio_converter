# Audio Converter

Fast, directory structure saving, parallel converter for audio files using `ffmpeg`

## Requirements

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

```json
{
    "input_dir": "G:\\music",
    "output_dir": "G:\\music_mp3",
    "threads": 12,
    "is_overwrite": false,
    "copy_other_files": true,
    "from_extensions": ["flac"],
    "to_extension": "mp3",
    "bitrate": "320k"
}
```

