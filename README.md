## Installation

Start in mtga_decklist_viewer root folder

Windows:

```powershell
py -m pip install -r requirements.txt -r mtga_utils/requirements.txt
cd mtga ; py setup.py install
```

Linux/macOS:

```bash
pip3 install -r requirements.txt -r mtga_utils/requirements.txt
cd mtga ; python3 setup.py install
```

## Notes

This project is using a forked version of `python-mtga` because it has not been updated to fix dynamic card scraping.
