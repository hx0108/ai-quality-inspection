"""补充照片到已导入的检查问题中"""
import sys, os, json, uuid, shutil
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, "/app")

from database import SessionLocal
from models.models import InspectionRecord, Issue, Photo

TASK_ID = "Q-20260312-d04fcec5"
PHOTOS_DIR = "/tmp/import_data/photos_import"
PHOTOS_STORAGE = "/app/data/photos"


def gen_id(prefix):
    today = datetime.now().strftime("%Y%m%d")
    return f"{prefix}-{today}-{uuid.uuid4().hex[:8]}"


def main():
    db = SessionLocal()
    try:
        # Load image map
        with open(os.path.join(PHOTOS_DIR, "image_map.json"), "r", encoding="utf-8") as f:
            image_map = json.load(f)

        records = db.query(InspectionRecord).filter(
            InspectionRecord.task_id == TASK_ID
        ).all()
        print(f"Found {len(records)} records")

        total_photos = 0

        for record in records:
            module_name = record.module_name
            module_image_map = image_map.get(module_name, {})
            if not module_image_map:
                print(f"  {module_name}: no photos in map")
                continue

            # Get all issues for this record
            issues = db.query(Issue).filter(Issue.record_id == record.record_id).all()
            print(f"\n  {module_name}: {len(issues)} issues, image rows: {list(module_image_map.keys())}")

            for issue in issues:
                # Extract item index from item_id like "安全-003"
                parts = issue.item_id.split("-")
                item_num = int(parts[1])  # e.g. 3
                # Excel row = item_num + 1 (because row_idx starts at 1, and data starts at row 2)
                excel_row = item_num + 1

                photo_files = module_image_map.get(str(excel_row), [])
                if not photo_files:
                    continue

                for pf in photo_files:
                    src = os.path.join(PHOTOS_DIR, module_name, pf)
                    if not os.path.exists(src):
                        print(f"    MISSING: {src}")
                        continue

                    # Copy to production storage
                    photo_dir = os.path.join(PHOTOS_STORAGE, record.record_id)
                    os.makedirs(photo_dir, exist_ok=True)
                    dst = os.path.join(photo_dir, pf)
                    shutil.copy2(src, dst)

                    photo_id = gen_id("PHO")
                    photo = Photo(
                        photo_id=photo_id,
                        issue_id=issue.issue_id,
                        file_path=dst,
                        file_name=pf,
                        photo_type="问题照片",
                    )
                    db.add(photo)
                    total_photos += 1
                    print(f"    {issue.item_id} (row {excel_row}): {pf}")

        db.commit()
        print(f"\n{'='*50}")
        print(f"照片补充完成: {total_photos} 张")

    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()
