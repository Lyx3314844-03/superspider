from __future__ import annotations

import argparse
import json
import urllib.request


def request_json(url: str, method: str = "GET", payload: dict | None = None) -> dict:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Minimal Python client for the shared spider /api/tasks contract")
    parser.add_argument("--base", required=True, help="Base /api/tasks URL")
    parser.add_argument("--url", required=True, help="Target URL to crawl")
    args = parser.parse_args(argv)

    created = request_json(args.base, method="POST", payload={"name": "python-client-demo", "url": args.url})
    task_id = created["data"]["id"]
    print(json.dumps({"created": task_id}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
