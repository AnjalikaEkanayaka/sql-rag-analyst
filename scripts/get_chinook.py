"""Download the Chinook SQLite sample database into data/chinook.db."""
import urllib.request
from pathlib import Path

URL = (
    "https://github.com/lerocha/chinook-database/raw/master/"
    "ChinookDatabase/DataSources/Chinook_Sqlite.sqlite"
)
DEST = Path("data/chinook.db")

DEST.parent.mkdir(exist_ok=True)
urllib.request.urlretrieve(URL, DEST)
print(f"Saved {DEST} ({DEST.stat().st_size / 1024:.0f} KB)")