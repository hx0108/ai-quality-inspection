"""从已完成的品质检查Excel中提取嵌入图片，按 sheet/row 组织"""
import sys, os
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import openpyxl
from PIL import Image
import io

EXCEL_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "..", "..", "F55金域蓝湾(蝶城版项目)品质检查报告.xlsx")
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "data", "photos_import")

os.makedirs(OUTPUT_DIR, exist_ok=True)

wb = openpyxl.load_workbook(EXCEL_PATH)

total_extracted = 0
# Mapping: {sheet_name: {excel_row: [filename1, filename2, ...]}}
image_map = {}

for name in wb.sheetnames:
    ws = wb[name]
    images = ws._images
    if not images:
        continue

    sheet_dir = os.path.join(OUTPUT_DIR, name)
    os.makedirs(sheet_dir, exist_ok=True)

    sheet_map = {}
    for i, img in enumerate(images):
        try:
            anchor = img.anchor
            if hasattr(anchor, "_from"):
                col_idx = anchor._from.col
                row_idx = anchor._from.row  # 0-indexed
            else:
                continue

            excel_row = row_idx + 1  # Convert to 1-indexed Excel row
            col_letter = chr(65 + col_idx)

            # Extract image data
            img_data = img._data()
            img_bytes = img_data.read() if hasattr(img_data, "read") else img_data

            # Save as JPEG
            filename = f"row{excel_row}_img{i}.jpg"
            filepath = os.path.join(sheet_dir, filename)

            # Convert to JPEG via PIL for consistency
            try:
                pil_img = Image.open(io.BytesIO(img_bytes))
                pil_img.save(filepath, "JPEG", quality=85)
            except Exception:
                with open(filepath, "wb") as f:
                    f.write(img_bytes)

            if excel_row not in sheet_map:
                sheet_map[excel_row] = []
            sheet_map[excel_row].append(filename)
            total_extracted += 1

        except Exception as e:
            print(f"  ERROR extracting image {i} from {name}: {e}")

    image_map[name] = sheet_map
    print(f"{name}: extracted {sum(len(v) for v in sheet_map.values())} images across {len(sheet_map)} rows")

# Save the mapping as JSON for the import script
import json
mapping_path = os.path.join(OUTPUT_DIR, "image_map.json")
with open(mapping_path, "w", encoding="utf-8") as f:
    json.dump(image_map, f, ensure_ascii=False, indent=2)

print(f"\nTotal extracted: {total_extracted} images")
print(f"Mapping saved to: {mapping_path}")
