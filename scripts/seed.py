"""Seed script: creates demo project and triggers inventory scan.

Usage:
    python3 scripts/seed.py
    python3 scripts/seed.py --project-name my-project --slug my-slug

Requires the app to be running (docker compose up).
"""

import argparse
import json
import urllib.request


BASE = "http://localhost:8000/api"


def api(path: str, method: str = "GET", body: dict | None = None) -> dict:
    req = urllib.request.Request(f"{BASE}{path}", method=method)
    req.add_header("Content-Type", "application/json")
    req.add_header("X-User", "seed-script")
    data = json.dumps(body).encode() if body else None
    with urllib.request.urlopen(req, data=data) as resp:
        return json.loads(resp.read())


def main():
    parser = argparse.ArgumentParser(description="Seed demo data for GitOps Platform")
    parser.add_argument("--project-name", default="ECP Platform", help="Project display name")
    parser.add_argument("--slug", default="ecp", help="Project slug")
    args = parser.parse_args()

    print(f"Creating project: {args.project_name} (slug: {args.slug})")
    project = api("/projects", method="POST", body={
        "name": args.project_name,
        "slug": args.slug,
        "github_org": "my-org",
        "github_repo": "ecp-infra",
        "terraform_root": "infra",
    })
    project_id = project["id"]
    print(f"  Project ID: {project_id}")

    print("Triggering inventory scan...")
    scan = api(f"/{project_id}/inventory/scan", method="POST")
    print(f"  Status: {scan['status']}")

    print("Checking inventory summary...")
    summary = api(f"/{project_id}/inventory/summary")
    kpis = summary["kpis"]
    print(f"  Total objects: {kpis['total_objects']}")
    print(f"  Resource types: {kpis['resource_types']}")
    print(f"  Environments: {kpis['environments']}")

    print("\nSeed completed. Open http://localhost:8000/ to view the UI.")


if __name__ == "__main__":
    main()
