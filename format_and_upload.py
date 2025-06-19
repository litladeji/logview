import os
import json
from datetime import datetime
from django.conf import settings
import django

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "logview.settings")
django.setup()

from logviewer.models import LogEntry

IMPORT_DIR = "imports"
PROCESSED_DIR = "media/logs"

def main():
    if not os.path.exists(PROCESSED_DIR):
        os.makedirs(PROCESSED_DIR)

    for filename in os.listdir(IMPORT_DIR):
        if not filename.endswith(".json"):
            continue

        filepath = os.path.join(IMPORT_DIR, filename)

        with open(filepath, "r") as f:
            try:
                data = json.load(f)

                log = LogEntry.objects.create(
                    station_id=data["station_id"],
                    timestamp=data["timestamp"],
                    metrics=data["metrics"],
                    result=data["result"],
                    filename=filename
                )
                print(f"✅ Uploaded: {filename}")
                os.rename(filepath, os.path.join(PROCESSED_DIR, filename))

            except Exception as e:
                print(f"❌ Failed to process {filename}: {e}")

if __name__ == "__main__":
    main()
