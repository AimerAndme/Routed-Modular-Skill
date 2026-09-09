"""Routed Modular Skill runtime: route, load, validate, execute, trace."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROUTE_THRESHOLD = 0.75
DEFAULT_ROUTE_MARGIN = 0.10


def contained_file(relative):
    if not isinstance(relative, str) or Path(relative).is_absolute():
        raise ValueError("Expected a relative resource path")
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT) or not path.is_file():
        raise ValueError("Missing resource or path outside skill root")
    return path


def catalog():
    data = json.loads((ROOT / "catalog.json").read_text(encoding="utf-8"))
    if data.get("schema_version") != 2 or not isinstance(data.get("modules"), list):
        raise ValueError("Unsupported catalog")
    result = {}
    for entry in data["modules"]:
        required = ("id", "when", "guide", "entrypoint", "input_schema", "output_schema", "hooks")
        if not isinstance(entry, dict) or any(key not in entry for key in required):
            raise ValueError("Invalid module metadata")
        if any(not isinstance(entry.get(key), str) or not entry[key]
               for key in ("id", "when", "guide", "entrypoint")):
            raise ValueError("Invalid module metadata")
        if entry["id"] in result or not isinstance(entry["hooks"], dict):
            raise ValueError("Duplicate module ID or invalid hooks")
        result[entry["id"]] = entry
    return result


def validate_schema(value, schema, location="$"):
    """Validate the intentionally small JSON Schema subset used by RMS."""
    if not isinstance(schema, dict):
        raise ValueError(f"Invalid schema at {location}")
    expected = schema.get("type")
    matches = {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "null": value is None,
    }
    if expected and (expected not in matches or not matches[expected]):
        raise ValueError(f"Schema validation failed at {location}: expected {expected}")
    if expected == "object":
        required = schema.get("required", [])
        properties = schema.get("properties", {})
        if not isinstance(required, list) or not isinstance(properties, dict):
            raise ValueError(f"Invalid object schema at {location}")
        missing = [key for key in required if key not in value]
        if missing:
            raise ValueError(f"Schema validation failed at {location}: missing {', '.join(missing)}")
        if schema.get("additionalProperties") is False:
            extra = sorted(set(value) - set(properties))
            if extra:
                raise ValueError(f"Schema validation failed at {location}: unexpected {', '.join(extra)}")
        for key, child in properties.items():
            if key in value:
                validate_schema(value[key], child, f"{location}.{key}")
    if expected == "array" and "items" in schema:
        for index, item in enumerate(value):
            validate_schema(item, schema["items"], f"{location}[{index}]")
    return value


def route(candidates, threshold=DEFAULT_ROUTE_THRESHOLD, margin=DEFAULT_ROUTE_MARGIN):
    entries = catalog()
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("Routing candidates must be a non-empty array")
    normalized = []
    for candidate in candidates:
        if not isinstance(candidate, dict) or candidate.get("id") not in entries:
            raise ValueError("Routing candidate contains unknown module ID")
        score = candidate.get("score")
        if not isinstance(score, (int, float)) or isinstance(score, bool) or not 0 <= score <= 1:
            raise ValueError("Routing score must be between 0 and 1")
        normalized.append({"id": candidate["id"], "score": float(score)})
    normalized.sort(key=lambda item: item["score"], reverse=True)
    winner = normalized[0]
    runner_up = normalized[1]["score"] if len(normalized) > 1 else 0.0
    if winner["score"] < threshold:
        return {"status": "needs_clarification", "reason": "below_threshold", "candidates": normalized}
    if len(normalized) > 1 and winner["score"] - runner_up < margin:
        return {"status": "needs_clarification", "reason": "ambiguous_margin", "candidates": normalized}
    return {"status": "selected", "module_id": winner["id"], "score": winner["score"]}


def event(trace, name, status="ok", detail=None):
    item = {"event": name, "status": status,
            "at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")}
    if detail is not None:
        item["detail"] = detail
    trace.append(item)


def run_hooks(phase, entry, value, trace):
    registered = entry["hooks"].get(phase, [])
    if not isinstance(registered, list):
        raise ValueError(f"Invalid {phase} hooks")
    for hook in registered:
        if hook == "validate-input-schema" and phase == "pre":
            validate_schema(value, entry["input_schema"])
        elif hook == "validate-output-schema" and phase == "post":
            validate_schema(value, entry["output_schema"])
        elif hook == "record-error" and phase == "on_error":
            pass
        else:
            raise ValueError(f"Unknown or misplaced hook: {hook}")
        event(trace, f"hook:{phase}:{hook}")


def persist_state(state_dir, state):
    if state_dir is None:
        return None
    directory = Path(state_dir).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{state['execution_id']}.json"
    temporary = directory / f".{state['execution_id']}.tmp"
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)
    return str(path)


def dispatch(command, module_id=None, payload=None, state_dir=None):
    entries = catalog()
    if command == "list":
        return [{key: item[key] for key in ("id", "when", "guide")} for item in entries.values()]
    if command == "route":
        return route(payload)
    if module_id not in entries:
        raise ValueError("Unknown module ID")
    entry = entries[module_id]
    if command == "load":
        guide = contained_file(entry["guide"])
        return {"module_id": module_id, "skill_root": str(ROOT),
                "guide_path": str(guide), "guide": guide.read_text(encoding="utf-8"),
                "shared_contract": str(contained_file("shared/CONTRACT.md")),
                "input_schema": entry["input_schema"], "output_schema": entry["output_schema"],
                "hooks": entry["hooks"]}
    if command != "run" or not isinstance(payload, dict):
        raise ValueError("run requires a JSON object")

    execution_id = str(uuid.uuid4())
    trace = []
    state = {"execution_id": execution_id, "module_id": module_id,
             "status": "running", "trace": trace}
    event(trace, "execution:started")
    try:
        run_hooks("pre", entry, payload, trace)
        script = contained_file(entry["entrypoint"])
        event(trace, "executor:started", detail={"entrypoint": entry["entrypoint"]})
        completed = subprocess.run(
            [sys.executable, str(script)], input=json.dumps(payload), text=True,
            encoding="utf-8", capture_output=True, cwd=ROOT, timeout=10,
        )
        if completed.returncode:
            raise ValueError("Module failed: " + completed.stderr.strip())
        output = json.loads(completed.stdout)
        if not isinstance(output, dict) or not isinstance(output.get("result"), dict):
            raise ValueError("Invalid module result")
        event(trace, "executor:completed")
        run_hooks("post", entry, output["result"], trace)
        state["status"] = "ok"
        state["result"] = output["result"]
        event(trace, "execution:completed")
        state_path = persist_state(state_dir, state)
        response = {"status": "ok", "execution_id": execution_id,
                    "module_id": module_id, "result": output["result"], "trace": trace}
        if state_path:
            response["state_path"] = state_path
        return response
    except (ValueError, OSError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
        event(trace, "execution:failed", status="error", detail={"error": str(exc)})
        try:
            run_hooks("on_error", entry, {"error": str(exc)}, trace)
        finally:
            state["status"] = "error"
            state["error"] = str(exc)
            persist_state(state_dir, state)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    subs.add_parser("list")
    subs.add_parser("load").add_argument("module_id")
    routing = subs.add_parser("route")
    routing.add_argument("--candidates", required=True, help="JSON candidate array")
    run = subs.add_parser("run")
    run.add_argument("module_id")
    run.add_argument("--input", required=True, help="JSON object")
    run.add_argument("--state-dir", help="Optional directory for execution state")
    args = parser.parse_args()
    try:
        if args.command == "run":
            payload = json.loads(args.input)
        elif args.command == "route":
            payload = json.loads(args.candidates)
        else:
            payload = None
        output = dispatch(args.command, getattr(args, "module_id", None), payload,
                          getattr(args, "state_dir", None))
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
