import json
import sys


def main():
    data = json.load(sys.stdin)
    if not isinstance(data, dict) or not isinstance(data.get("text"), str):
        raise ValueError("text must be a string")
    print(json.dumps({"result": {"text": data["text"].upper()}}, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, TypeError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
