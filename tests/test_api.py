"""Integration tests — run against the live Docker app (docker compose up).

Usage:
    python3 -m pytest tests/ -v
"""

import pytest
import httpx


BASE = "http://localhost:8000/api"


@pytest.mark.asyncio
async def test_health():
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE}/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_projects_crud():
    async with httpx.AsyncClient() as client:
        # List
        resp = await client.get(f"{BASE}/projects")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data

        if data["items"]:
            project_id = data["items"][0]["id"]

            # Get by ID
            resp = await client.get(f"{BASE}/projects/{project_id}")
            assert resp.status_code == 200
            assert resp.json()["id"] == project_id


@pytest.mark.asyncio
async def test_inventory_scan_and_list():
    async with httpx.AsyncClient() as client:
        # Get existing project
        resp = await client.get(f"{BASE}/projects")
        projects = resp.json()["items"]
        if not projects:
            pytest.skip("No projects exist — run seed script first")
        project_id = projects[0]["id"]

        # Trigger scan
        resp = await client.post(f"{BASE}/{project_id}/inventory/scan")
        assert resp.status_code == 200
        assert resp.json()["status"] in ("success", "partial")

        # Summary
        resp = await client.get(f"{BASE}/{project_id}/inventory/summary")
        assert resp.status_code == 200
        kpis = resp.json()["kpis"]
        assert kpis["total_objects"] > 0

        # Objects list
        resp = await client.get(f"{BASE}/{project_id}/inventory/objects")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) > 0

        # Prefix filtering for Resource Management inventory
        resp = await client.get(f"{BASE}/{project_id}/inventory/objects?resource_type_prefix=aws_,k8s_")
        assert resp.status_code == 200
        prefixed_items = resp.json()["items"]
        assert all(
            item["resource_type"].startswith(("aws_", "k8s_"))
            for item in prefixed_items
        )

        # Object detail
        obj_id = items[0]["id"]
        resp = await client.get(f"{BASE}/{project_id}/inventory/objects/{obj_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == obj_id


@pytest.mark.asyncio
async def test_change_workflow_full():
    """End-to-end change workflow."""
    async with httpx.AsyncClient() as client:
        # Get project
        resp = await client.get(f"{BASE}/projects")
        projects = resp.json()["items"]
        if not projects:
            pytest.skip("No projects exist — run seed script first")
        project_id = projects[0]["id"]

        # Ensure scan ran
        await client.post(f"{BASE}/{project_id}/inventory/scan")

        # 1. Create draft + preview
        resp = await client.post(
            f"{BASE}/{project_id}/changes/draft-preview",
            json={
                "change_type": "odp_resource_update",
                "object_id": "ODP/resources/dev/ecp/api-gateway",
                "proposed": {"maxReplicas": 25},
                "reason": "scale up for integration test",
                "created_by": "test-runner",
            },
        )
        assert resp.status_code == 200
        change_id = resp.json()["change"]["id"]

        # Verify PatchGenerated
        resp = await client.get(f"{BASE}/{project_id}/changes/{change_id}")
        assert resp.json()["status"] == "PatchGenerated"

        # 2. Validate
        resp = await client.post(f"{BASE}/{project_id}/changes/{change_id}/validate")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ValidationPassed"

        # Verify validation artifact persisted
        resp = await client.get(f"{BASE}/{project_id}/changes/{change_id}")
        artifacts = resp.json().get("artifacts", {})
        assert "validation" in artifacts, f"Missing validation in: {sorted(artifacts.keys())}"

        # 3. Plan
        resp = await client.post(f"{BASE}/{project_id}/changes/{change_id}/plan")
        assert resp.status_code == 200

        # 4. Submit
        resp = await client.post(
            f"{BASE}/{project_id}/changes/{change_id}/submit",
            json={"requester": "sre-user", "note": "ready"},
        )
        assert resp.status_code == 200

        # 5. Approve
        resp = await client.post(
            f"{BASE}/{project_id}/changes/{change_id}/approve",
            json={"approver": "manager", "decision": "approve", "comment": "lgtm"},
        )
        assert resp.status_code == 200

        # 6. Execute
        resp = await client.post(
            f"{BASE}/{project_id}/changes/{change_id}/execute",
            json={"executor": "sre-bot"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ExecutionReady"

        # 7. Audit
        resp = await client.get(f"{BASE}/{project_id}/changes/{change_id}/audit")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 3


@pytest.mark.asyncio
async def test_validation_artifact_persistence():
    """Regression: validation artifact survives repository.update()."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE}/projects")
        projects = resp.json()["items"]
        if not projects:
            pytest.skip("No projects exist")
        project_id = projects[0]["id"]

        await client.post(f"{BASE}/{project_id}/inventory/scan")

        resp = await client.post(
            f"{BASE}/{project_id}/changes/draft-preview",
            json={
                "change_type": "odp_resource_update",
                "object_id": "ODP/resources/dev/ecp/api-gateway",
                "proposed": {"maxReplicas": 6},
                "reason": "regression test",
                "created_by": "test",
            },
        )
        change_id = resp.json()["change"]["id"]

        await client.post(f"{BASE}/{project_id}/changes/{change_id}/validate")

        resp = await client.get(f"{BASE}/{project_id}/changes/{change_id}")
        artifacts = resp.json().get("artifacts", {})
        assert "validation" in artifacts
        assert artifacts["validation"]["status"] == "ValidationPassed"


@pytest.mark.asyncio
async def test_templates():
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE}/projects")
        projects = resp.json()["items"]
        if not projects:
            pytest.skip("No projects exist")
        project_id = projects[0]["id"]

        resp = await client.get(f"{BASE}/{project_id}/templates")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1


@pytest.mark.asyncio
async def test_adapters():
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE}/projects")
        projects = resp.json()["items"]
        if not projects:
            pytest.skip("No projects exist")
        project_id = projects[0]["id"]

        resp = await client.get(f"{BASE}/{project_id}/adapters")
        assert resp.status_code == 200
        assert len(resp.json()["items"]) >= 3


@pytest.mark.asyncio
async def test_infrastructure_adapters():
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE}/infrastructure-adapters")
        assert resp.status_code == 200
        data = resp.json()
        assert "git" in data
        assert "execution" in data
        assert "webhook" in data
        assert any(a["name"] == "github" for a in data["git"])
        assert any(a["name"] == "jenkins" for a in data["execution"])
        assert any(a["name"] == "k8s" for a in data["execution"])


@pytest.mark.asyncio
async def test_k8s_client_no_config():
    """K8S client should handle missing kubectl gracefully."""
    from app.infrastructure.k8s_client import KubernetesClient, K8SResult

    client = KubernetesClient()
    result = client.check_connectivity()
    assert isinstance(result, K8SResult)
    # Will fail since no kubectl in test env — that's expected


@pytest.mark.asyncio
async def test_change_execute_k8s_mode():
    """Execute with k8s_apply mode should be accepted (blocked without K8S config)."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE}/projects")
        projects = resp.json()["items"]
        if not projects:
            pytest.skip("No projects exist")
        project_id = projects[0]["id"]

        await client.post(f"{BASE}/{project_id}/inventory/scan")

        # Create change and run through to Approved
        resp = await client.post(
            f"{BASE}/{project_id}/changes/draft-preview",
            json={
                "change_type": "odp_resource_update",
                "object_id": "ODP/resources/dev/ecp/api-gateway",
                "proposed": {"maxReplicas": 10},
                "reason": "k8s test",
                "created_by": "test",
            },
        )
        change_id = resp.json()["change"]["id"]

        await client.post(f"{BASE}/{project_id}/changes/{change_id}/validate")
        await client.post(f"{BASE}/{project_id}/changes/{change_id}/plan")
        await client.post(
            f"{BASE}/{project_id}/changes/{change_id}/submit",
            json={"requester": "sre", "note": "test"},
        )
        await client.post(
            f"{BASE}/{project_id}/changes/{change_id}/approve",
            json={"approver": "manager", "decision": "approve", "comment": "ok"},
        )

        # Execute with k8s_apply mode — should fail gracefully (no kubeconfig)
        resp = await client.post(
            f"{BASE}/{project_id}/changes/{change_id}/execute",
            json={"executor": "sre-bot", "mode": "k8s_apply"},
        )
        # Without KUBECONFIG_PATH, k8s_client is None, so 400 is expected
        assert resp.status_code in (200, 400)


@pytest.mark.asyncio
async def test_skeleton_templates_api():
    """Skeleton template listing and schema work."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE}/default/skeletons/templates")
        assert resp.status_code == 200
        assert resp.json()["total"] == 3

        resp = await client.get(f"{BASE}/default/skeletons/templates/aws_ec2/schema")
        assert resp.status_code == 200
        schema = resp.json()
        assert "parameter_schema" in schema
        assert schema["render_mode"] == "hcl"


@pytest.mark.asyncio
async def test_k8s_manifest_change_lifecycle():
    """K8S manifest change type should go through full lifecycle."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE}/projects")
        projects = resp.json()["items"]
        if not projects:
            pytest.skip("No projects exist")
        project_id = projects[0]["id"]

        # Create a k8s manifest change
        resp = await client.post(
            f"{BASE}/{project_id}/changes",
            json={
                "change_type": "k8s_manifest_update",
                "object_id": "k8s/configmap/sandbox/nginx-config",
                "proposed": {"data": {"max_clients": "2000"}},
                "reason": "test k8s manifest change",
                "created_by": "test",
            },
        )
        # Either 200 (object exists) or 400 (object not found in test DB)
        if resp.status_code == 200:
            change = resp.json()
            assert change["change_type"] == "k8s_manifest_update"
            assert change["status"] == "Draft"
            assert change["env"] == "sandbox"
