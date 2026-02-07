import os
import json
from pymongo import MongoClient
from tqdm import tqdm

# ===== MongoDB Connection =====
client = MongoClient("mongodb://localhost:27017/")
db = client["legal_cases"]
collection = db["cases"]

# ===== JSON Folder =====
JSON_FOLDER = "data/processed/extracted_json"

def import_all_json():
    files = [f for f in os.listdir(JSON_FOLDER) if f.endswith(".json")]

    print(f"📂 Total JSON files found: {len(files)}")

    for file in tqdm(files, desc="Importing to MongoDB"):
        file_path = os.path.join(JSON_FOLDER, file)

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Avoid duplicates using case_id
            collection.update_one(
                {"case_id": data.get("case_id")},
                {"$set": data},
                upsert=True
            )

        except Exception as e:
            print(f"❌ Failed: {file} → {e}")

    print("✅ All JSON files imported successfully!")

if __name__ == "__main__":
    import_all_json()
