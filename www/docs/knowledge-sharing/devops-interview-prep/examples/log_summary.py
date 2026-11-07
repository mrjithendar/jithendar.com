"""Summarise an Nginx access log: status mix, top 5xx paths, p95 latency per path."""
import math
import re
import sys
from collections import Counter, defaultdict

# Combined log format with $request_time appended as the last field.
LINE = re.compile(
    r'(?P<ip>\S+) \S+ \S+ \[(?P<ts>[^\]]+)\] '
    r'"(?P<method>[A-Z]+) (?P<path>[^ ?"]+)[^"]*" '
    r'(?P<status>\d{3}) (?P<size>\d+|-) "[^"]*" "[^"]*" (?P<rt>\d+(?:\.\d+)?)$'
)


def parse(lines):
    """Yield one dict per valid line. A generator, so a 20 GB log never sits in memory."""
    for line in lines:
        match = LINE.match(line.rstrip("\n"))
        if match:
            yield match.groupdict()


def p95(values):
    ordered = sorted(values)
    return ordered[math.ceil(0.95 * len(ordered)) - 1]  # nearest-rank


def summarise(lines):
    statuses, errors, latency = Counter(), Counter(), defaultdict(list)
    for rec in parse(lines):
        statuses[rec["status"]] += 1
        if rec["status"].startswith("5"):
            errors[rec["path"]] += 1
        latency[rec["path"]].append(float(rec["rt"]))
    return {
        "statuses": dict(statuses),
        "top_5xx": errors.most_common(5),
        "p95": {path: p95(v) for path, v in latency.items()},
    }


if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8", errors="replace") as fh:
        report = summarise(fh)
    print("status codes:", report["statuses"])
    print("top 5xx paths:", report["top_5xx"])
    for path, value in sorted(report["p95"].items(), key=lambda kv: -kv[1])[:5]:
        print(f"p95 {value:.3f}s  {path}")
