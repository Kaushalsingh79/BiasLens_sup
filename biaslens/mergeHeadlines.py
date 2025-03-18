import json
import glob
import os


def merge_json_files(output_file="merged.json"):
    combined_data = []

    for file_path in glob.glob("*.json"):
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                combined_data.extend(data)
            elif isinstance(data, dict):
                combined_data.append(data)

    with open(output_file, "w", encoding="utf-8") as out_file:
        json.dump(combined_data, out_file, indent=4)


if __name__ == "__main__":
    merge_json_files()
