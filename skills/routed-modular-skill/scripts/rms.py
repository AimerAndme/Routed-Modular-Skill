"""Explicit routing and lazy guide loading. Trusted local modules only."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def contained_file(relative):
    if not isinstance(relative, str) or Path(relative).is_absolute():
        raise ValueError("Expected a relative resource path")
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT) or not path.is_file():
        raise ValueError("Missing resource or path outside skill root")
    return path


def catalog():
    data = json.loads((ROOT / "catalog.json").read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or not isinstance(data.get("modules"), list):
        raise ValueError("Unsupported catalog")
    result = {}
    for entry in data["modules"]:
        if not isinstance(entry, dict) or any(
            not isinstance(entry.get(key), str) or not entry[key]
            for key in ("id", "when", "guide", "entrypoint")
        ):
            raise ValueError("Invalid module metadata")
        if entry["id"] in result:
            raise ValueError("Duplicate module ID")
        result[entry["id"]] = entry
    return result


def dispatch(command, module_id=None, payload=None):
    entries = catalog()
    if command == "list":
        return [{key: item[key] for key in ("id", "when", "guide")} for item in entries.values()]
    if module_id not in entries:
        raise ValueError("Unknown module ID")
    entry = entries[module_id]
    if command == "load":
        guide = contained_file(entry["guide"])
        return {"module_id": module_id, "skill_root": str(ROOT),
                "guide_path": str(guide), "guide": guide.read_text(encoding="utf-8"),
                "shared_contract": str(contained_file("shared/CONTRACT.md"))}
    if command != "run" or not isinstance(payload, dict):
        raise ValueError("run requires a JSON object")
    script = contained_file(entry["entrypoint"])
    completed = subprocess.run(
        [sys.executable, str(script)], input=json.dumps(payload),
        text=True, encoding="utf-8", capture_output=True, cwd=ROOT, timeout=10,
    )
    if completed.returncode:
        raise ValueError("Module failed: " + completed.stderr.strip())
    output = json.loads(completed.stdout)
    if not isinstance(output, dict) or not isinstance(output.get("result"), dict):
        raise ValueError("Invalid module result")
    return {"status": "ok", "module_id": module_id, "result": output["result"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    subs.add_parser("list")
    subs.add_parser("load").add_argument("module_id")
    run = subs.add_parser("run")
    run.add_argument("module_id")
    run.add_argument("--input", required=True, help="JSON object")
    args = parser.parse_args()
    try:
        payload = json.loads(args.input) if args.command == "run" else None
        output = dispatch(args.command, getattr(args, "module_id", None), payload)
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
