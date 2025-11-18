from __future__ import annotations
import json
import argparse

parser = argparse.ArgumentParser(description="Parse a JSON file and print the keys.")

parser.add_argument("filename", help="The name of the file to process.")
parser.add_argument("--from-key", type=str, default="", help="Key to parse this from.")
parser.add_argument("--keys", type=bool, default=True, help="Depth to parse to.")
parser.add_argument("--compressed", type=bool, default=True, help="Depth to parse to.")
args = parser.parse_args()


def keys(dictionary: dict) -> dict[str, dict]:
        found = {}
        for key in dictionary.keys():
                found[key] = {}
                if isinstance(dictionary[key], dict):
                        found[key] = keys(dictionary[key])
                elif isinstance(dictionary[key], list):
                        first = dictionary[key][0]
                        if isinstance(first, dict):
                                found[key] = keys(first)
        return found

def print_keys(found: dict[str, dict], depth: int = 0):
        for k, v in found.items():
                print(f"{'  ' * depth}{k}")
                if isinstance(v, dict):
                        print_keys(v, depth + 1)


def compress(dictionary: dict, depth: int = 0):
        for k, v in dictionary.items():
                if isinstance(v, dict):
                        dictionary[k] = compress(v)
                if isinstance(v, list):
                        if isinstance(v[0], dict):
                                dictionary[k] = [compress(v[0])]
                        else:
                                dictionary[k] = [v[0], v[-1]]

                elif isinstance(v, str):
                        if len(v) > 10:
                                dictionary[k] = f"{v[:50]}..."
                        else:
                                dictionary[k] = v
        return dictionary



with open(args.filename) as f:
        content = f.read()
        data = json.loads(content)
        if args.from_key:
                data = data.get(args.from_key, data)

        if args.keys:
            print("Discovered keys:\n")
            found = keys(data)
            print(json.dumps(found, indent=4))
            print('-' * 80)

        if args.compressed:
            print("Compressed data:\n")
            compressed = compress(data)
            print(json.dumps(compressed, indent=4))
            print('-' * 80)
