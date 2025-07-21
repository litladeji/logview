import os
import json
from datetime import datetime
from django.conf import settings
import django




# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "logview.settings")
django.setup()

from logviewer.models import LogEntry, Test, Overall_Summary, Test_Type, Test_Type_Form

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
            # try:
            data = json.load(f)
            created_ts = datetime.fromtimestamp(data.get("created", datetime.now().timestamp())) #tries to get the date cretaed form the data from the key-"created" and if it does'nt exists it uses the curret time


            # log = LogEntry.objects.create(
            #     station_id=data["station_id"],
            #     timestamp=data["timestamp"],
            #     metrics=data["metrics"],
            #     result=data["result"],
            #     filename=filename
            # )
            
      

            # Metadata
            meta_common = {
                "branch": data.get("branch", "NO_BRANCH"),
                "commit_hash": data.get("commit_hash", "NO_COMMIT_HASH"),
                "remote_url": data.get("remote_url", "NO_URL"),
                "status": data.get("status", "NO_STATUS"),
                "firmware_name": data.get("firmware_name", "NO_FIRMWARE_NAME"),
                "firmware_git_desc": data.get("firmware_git_desc", "NO_GIT_DESC"),
            }

            # Default barcode
            barcode = data.get("chip_number") or "null_CHIP_ID"

            # Loop through test entries
            for test in data.get("tests", []):
                metadata = test.get("metadata", {})
                Test.objects.create(
                    test_name=test["nodeid"],
                    barcode=barcode,
                    tester="AutoTester",
                    date_run=str(created_ts),
                    outcome=test["outcome"],
                    valid=True,
                    overwrite_pass=False,
                    eRX_errcounts=bytes(str(metadata.get("eRX_errcounts", [])), encoding='utf-8'),
                    eTX_delays=bytes(str(metadata.get("eTX_delays", [])), encoding='utf-8'),
                    eTX_bitcounts=bytes(str(metadata.get("eTX_bitcounts", [])), encoding='utf-8'),
                    eTX_errcounts=bytes(str(metadata.get("eTX_errcounts", [])), encoding='utf-8'),
                    longrepr=test.get("call", {}).get("log", [{}])[0].get("exc_text", "") if test.get("call", {}).get("log") else "",
                    stdout=test.get("setup", {}).get("stdout", ""),
                    crashpath="",
                    crashmsg="",
                    filename=filename,
                    ECON_TYPE="ECOND" if "ECOND" in test.get("keywords", []) else "ECONT",
                    comments="",
                    **meta_common
                )

            # Generate test type summary
            test_type_counts = {}
            for test in data.get("tests", []):
                name = test["nodeid"].split("::")[-1]
                test_type_counts.setdefault(name, {"passed": 0, "failed": 0})
                if test["outcome"] == "passed":
                    test_type_counts[name]["passed"] += 1
                else:
                    test_type_counts[name]["failed"] += 1

            test_type_array = []
            for name, counts in test_type_counts.items():
                test_type_array.append({
                        "test_name":name,
                        "number_passed":counts["passed"],
                        "number_failed":counts["failed"],
                        "number_total":counts["passed"] + counts["failed"],
                        "required":True # type: ignore
                    }
                    
                )

            # Save Overall_Summary
            Overall_Summary.objects.create(
                test_types=test_type_array,
                passedcards=data["summary"]["passed"],
                failedcards=data["summary"]["total"] - data["summary"]["passed"],
                totalcards=data["summary"]["total"]
            )

            print(f"✅ Uploaded: {filename}")
            os.rename(filepath, os.path.join(PROCESSED_DIR, filename))
            # except Exception as e:
            #     print(f"❌ Failed to process {filename}: {e}")

if __name__ == "__main__":
    main()
