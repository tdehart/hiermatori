import json
import sys
import re
from datetime import datetime
import time


def sanitize_key(key):
    """Trim leading and trailing whitespace from keys."""
    return key.strip()


def sanitize_value(value):
    """Trim leading and trailing whitespace from string values."""
    if isinstance(value, str):
        return value.strip()
    return value


def is_rfc3339(s):
    """Check if the string is in RFC3339 format."""
    try:
        datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")
        return True
    except ValueError:
        return False


def rfc3339_to_epoch(s):
    """Convert RFC3339 string to Unix Epoch."""
    dt = datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")
    return int(time.mktime(dt.timetuple()))


def process_string(field_value):
    """Process String (`S`) data type."""
    value = sanitize_value(field_value)
    if not value:
        return None
    if is_rfc3339(value):
        return rfc3339_to_epoch(value)
    return value


def process_number(field_value):
    """Process Number (`N`) data type."""
    value = sanitize_value(field_value)
    # Remove leading zeros
    if value.startswith("-0"):
        value = "-" + re.sub(r"^-?0+", "", value)
    else:
        value = re.sub(r"^0+(?=\d)", "", value)
    try:
        if "." in value:
            return float(value)
        else:
            return int(value)
    except ValueError:
        return None


def process_boolean(field_value):
    """Process Boolean (`BOOL`) data type."""
    value = sanitize_value(field_value).lower()
    true_values = {"1", "t", "true"}
    false_values = {"0", "f", "false"}
    if value in true_values:
        return True
    elif value in false_values:
        return False
    return None


def process_null(field_value):
    """Process Null (`NULL`) data type."""
    value = sanitize_value(field_value).lower()
    true_values = {"1", "t", "true"}
    false_values = {"0", "f", "false"}
    if value in true_values:
        return None
    elif value in false_values:
        return "omit"
    return "omit"


def process_list(field_value):
    """Process List (`L`) data type."""
    if not isinstance(field_value, list):
        return None
    processed_list = []
    for item in field_value:
        if not isinstance(item, dict) or len(item) != 1:
            continue
        key, val = next(iter(item.items()))
        if key == "S":
            processed = process_string(val)
            if processed is not None:
                processed_list.append(processed)
        elif key == "N":
            processed = process_number(val)
            if processed is not None:
                processed_list.append(processed)
        elif key == "BOOL":
            processed = process_boolean(val)
            if processed is not None:
                processed_list.append(processed)
        # NULL, L, M are omitted in lists as per criteria
        else:
            continue
    if not processed_list:
        return None
    return processed_list


def process_map(field_value):
    """Process Map (`M`) data type."""
    if not isinstance(field_value, dict):
        return None
    processed_map = {}
    for raw_key, item in field_value.items():
        key = sanitize_key(raw_key)
        if not key:
            continue
        if not isinstance(item, dict) or len(item) != 1:
            continue
        type_key, val = next(iter(item.items()))
        if type_key == "S":
            processed = process_string(val)
            if processed is not None:
                processed_map[key] = processed
        elif type_key == "N":
            processed = process_number(val)
            if processed is not None:
                processed_map[key] = processed
        elif type_key == "BOOL":
            processed = process_boolean(val)
            if processed is not None:
                processed_map[key] = processed
        elif type_key == "NULL":
            processed = process_null(val)
            if processed is None:
                processed_map[key] = None
            elif processed == "omit":
                continue
            else:
                processed_map[key] = processed
        elif type_key == "L":
            processed = process_list(val)
            if processed is not None:
                processed_map[key] = processed
        elif type_key == "M":
            processed = process_map(val)
            if processed is not None:
                processed_map[key] = processed
        else:
            continue
    if not processed_map:
        return None
    # Lexically sort the map
    sorted_map = dict(sorted(processed_map.items()))
    return sorted_map


def transform_input(input_json):
    """Transform the input JSON according to the specified criteria."""
    processed = {}
    for raw_key, item in input_json.items():
        key = sanitize_key(raw_key)
        if not key:
            continue
        if not isinstance(item, dict) or len(item) != 1:
            continue
        type_key, val = next(iter(item.items()))
        if type_key == "S":
            processed_value = process_string(val)
            if processed_value is not None:
                processed[key] = processed_value
        elif type_key == "N":
            processed_value = process_number(val)
            if processed_value is not None:
                processed[key] = processed_value
        elif type_key == "BOOL":
            processed_value = process_boolean(val)
            if processed_value is not None:
                processed[key] = processed_value
        elif type_key == "NULL":
            processed_value = process_null(val)
            if processed_value is None:
                processed[key] = None
            elif processed_value == "omit":
                continue
        elif type_key == "L":
            processed_value = process_list(val)
            if processed_value is not None:
                processed[key] = processed_value
        elif type_key == "M":
            processed_value = process_map(val)
            if processed_value is not None:
                processed[key] = processed_value
        else:
            continue
    if not processed:
        return []
    # Wrap the processed object in a list
    return [processed]


def main():
    start_time = time.time()  # Start timer

    # Read input JSON from stdin
    input_data = sys.stdin.read()
    try:
        input_json = json.loads(input_data)
    except json.JSONDecodeError:
        print("Invalid JSON input.", file=sys.stderr)
        sys.exit(1)

    transformed = transform_input(input_json)
    output_json = json.dumps(transformed, indent=2)
    print(output_json)

    end_time = time.time()  # End timer
    processing_time = end_time - start_time
    print(f"\nProcessing Time: {processing_time:.6f} seconds", file=sys.stderr)


if __name__ == "__main__":
    main()
