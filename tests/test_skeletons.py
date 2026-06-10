"""Integration tests for the Skeleton (scaffolding) system.

Usage:
    python3 -m pytest tests/test_skeletons.py -v
"""

import pytest
import httpx


BASE = "http://localhost:8000/api"

KNOWN_TEMPLATES = {"odp_hype_level", "odp_resource", "aws_ec2"}

# Valid params for each template
VALID_PARAMS = {
    "odp_hype_level": {"env": "dev", "cluster_id": "ecp-shanghai", "profile": "ecp"},
    "odp_resource": {"env": "dev", "component": "api-gateway"},
    "aws_ec2": {
        "city": "shanghai",
        "env": "prod",
        "instance_type": "t3.medium",
        "instance_name": "web",
    },
}

# Expected minimum file counts per template
MIN_FILES = {
    "odp_hype_level": 2,
    "odp_resource": 2,
    "aws_ec2": 5,
}


async def _get_project_id(client: httpx.AsyncClient) -> str | None:
    """Return the first project ID, or None if no projects exist."""
    resp = await client.get(f"{BASE}/projects")
    data = resp.json()
    items = data.get("items", [])
    return items[0]["id"] if items else None


# ---------------------------------------------------------------------------
# Template listing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_skeleton_templates_list():
    """GET /skeletons/templates returns at least 3 known templates."""
    async with httpx.AsyncClient() as client:
        project_id = await _get_project_id(client)
        if not project_id:
            pytest.skip("No projects exist — run seed script first")

        resp = await client.get(f"{BASE}/{project_id}/skeletons/templates")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 3, f"Expected >= 3 templates, got {data['total']}"

        ids = {t["id"] for t in data["items"]}
        for tid in KNOWN_TEMPLATES:
            assert tid in ids, f"Expected template '{tid}' in response"


@pytest.mark.asyncio
async def test_skeleton_filter_by_provider():
    """GET /skeletons/templates?provider=ODP returns 2 ODP templates."""
    async with httpx.AsyncClient() as client:
        project_id = await _get_project_id(client)
        if not project_id:
            pytest.skip("No projects exist — run seed script first")

        resp = await client.get(
            f"{BASE}/{project_id}/skeletons/templates", params={"provider": "ODP"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2, f"Expected 2 ODP templates, got {data['total']}"

        ids = {t["id"] for t in data["items"]}
        assert ids == {"odp_hype_level", "odp_resource"}, (
            f"Expected odp_hype_level & odp_resource, got {ids}"
        )


@pytest.mark.asyncio
async def test_skeleton_filter_by_render_mode():
    """GET /skeletons/templates?render_mode=hcl returns only aws_ec2."""
    async with httpx.AsyncClient() as client:
        project_id = await _get_project_id(client)
        if not project_id:
            pytest.skip("No projects exist — run seed script first")

        resp = await client.get(
            f"{BASE}/{project_id}/skeletons/templates",
            params={"render_mode": "hcl"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1, f"Expected 1 HCL template, got {data['total']}"

        ids = {t["id"] for t in data["items"]}
        assert ids == {"aws_ec2"}, f"Expected aws_ec2 only, got {ids}"


# ---------------------------------------------------------------------------
# Single template retrieval
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_skeleton_get_single_template():
    """GET /skeletons/templates/aws_ec2 returns full template metadata."""
    async with httpx.AsyncClient() as client:
        project_id = await _get_project_id(client)
        if not project_id:
            pytest.skip("No projects exist — run seed script first")

        resp = await client.get(
            f"{BASE}/{project_id}/skeletons/templates/aws_ec2"
        )
        assert resp.status_code == 200
        data = resp.json()

        assert data["id"] == "aws_ec2"
        assert "linked_template_id" in data, "Missing linked_template_id"
        assert "directories" in data, "Missing directories"
        assert "parameter_schema" in data, "Missing parameter_schema"
        assert isinstance(data["directories"], list)
        assert isinstance(data["parameter_schema"], dict)


@pytest.mark.asyncio
async def test_skeleton_get_schema():
    """GET /skeletons/templates/aws_ec2/schema returns schema with required."""
    async with httpx.AsyncClient() as client:
        project_id = await _get_project_id(client)
        if not project_id:
            pytest.skip("No projects exist — run seed script first")

        resp = await client.get(
            f"{BASE}/{project_id}/skeletons/templates/aws_ec2/schema"
        )
        assert resp.status_code == 200
        data = resp.json()

        assert "parameter_schema" in data, "Missing parameter_schema in schema response"
        schema = data["parameter_schema"]
        assert "required" in schema, "Schema missing 'required' field"
        assert len(schema["required"]) >= 1, (
            f"Expected at least 1 required field, got {schema.get('required')}"
        )


@pytest.mark.asyncio
async def test_skeleton_get_nonexistent_template():
    """GET /skeletons/templates/nonexistent returns 404."""
    async with httpx.AsyncClient() as client:
        project_id = await _get_project_id(client)
        if not project_id:
            pytest.skip("No projects exist — run seed script first")

        resp = await client.get(
            f"{BASE}/{project_id}/skeletons/templates/nonexistent"
        )
        assert resp.status_code == 404, (
            f"Expected 404 for nonexistent template, got {resp.status_code}"
        )


# ---------------------------------------------------------------------------
# linked_template_id check
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_skeleton_linked_template_id():
    """Every template returned in the list has a linked_template_id field."""
    async with httpx.AsyncClient() as client:
        project_id = await _get_project_id(client)
        if not project_id:
            pytest.skip("No projects exist — run seed script first")

        resp = await client.get(f"{BASE}/{project_id}/skeletons/templates")
        assert resp.status_code == 200
        data = resp.json()

        for item in data["items"]:
            assert "linked_template_id" in item, (
                f"Template '{item.get('id')}' missing linked_template_id"
            )


# ---------------------------------------------------------------------------
# Preview
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_skeleton_preview_yaml():
    """POST /skeletons/preview with odp_hype_level + valid params succeeds."""
    async with httpx.AsyncClient() as client:
        project_id = await _get_project_id(client)
        if not project_id:
            pytest.skip("No projects exist — run seed script first")

        resp = await client.post(
            f"{BASE}/{project_id}/skeletons/preview",
            json={
                "template_id": "odp_hype_level",
                "params": VALID_PARAMS["odp_hype_level"],
            },
        )
        assert resp.status_code == 200, (
            f"Preview YAML failed with {resp.status_code}: {resp.text}"
        )
        data = resp.json()
        assert "files" in data, "Missing 'files' in preview response"
        assert len(data["files"]) >= MIN_FILES["odp_hype_level"], (
            f"Expected >= {MIN_FILES['odp_hype_level']} files, got {len(data['files'])}"
        )


@pytest.mark.asyncio
async def test_skeleton_preview_hcl():
    """POST /skeletons/preview with aws_ec2 + valid params generates >= 5 files."""
    async with httpx.AsyncClient() as client:
        project_id = await _get_project_id(client)
        if not project_id:
            pytest.skip("No projects exist — run seed script first")

        resp = await client.post(
            f"{BASE}/{project_id}/skeletons/preview",
            json={
                "template_id": "aws_ec2",
                "params": VALID_PARAMS["aws_ec2"],
            },
        )
        assert resp.status_code == 200, (
            f"Preview HCL failed with {resp.status_code}: {resp.text}"
        )
        data = resp.json()
        assert "files" in data, "Missing 'files' in preview response"

        files = data["files"]
        assert len(files) >= MIN_FILES["aws_ec2"], (
            f"Expected >= {MIN_FILES['aws_ec2']} files, got {len(files)}"
        )

        # Verify key HCL files are present (paths include directory hierarchy)
        file_names = {f["path"].split("/")[-1] for f in files}
        expected_files = {"main.tf", "variables.tf", "outputs.tf", "terraform.tfvars"}
        for ef in expected_files:
            assert ef in file_names, f"Expected '{ef}' in generated files, got {file_names}"


@pytest.mark.asyncio
async def test_skeleton_preview_missing_params():
    """POST /skeletons/preview with missing required params returns 400."""
    async with httpx.AsyncClient() as client:
        project_id = await _get_project_id(client)
        if not project_id:
            pytest.skip("No projects exist — run seed script first")

        resp = await client.post(
            f"{BASE}/{project_id}/skeletons/preview",
            json={
                "template_id": "aws_ec2",
                "params": {},  # no required params
            },
        )
        assert resp.status_code == 400, (
            f"Expected 400 for missing params, got {resp.status_code}: {resp.text}"
        )


@pytest.mark.asyncio
async def test_skeleton_preview_nonexistent_template():
    """POST /skeletons/preview with nonexistent template returns 404 or 400."""
    async with httpx.AsyncClient() as client:
        project_id = await _get_project_id(client)
        if not project_id:
            pytest.skip("No projects exist — run seed script first")

        resp = await client.post(
            f"{BASE}/{project_id}/skeletons/preview",
            json={
                "template_id": "nonexistent",
                "params": {"env": "dev"},
            },
        )
        assert resp.status_code in (400, 404), (
            f"Expected 400 or 404 for nonexistent template, got {resp.status_code}"
        )


# ---------------------------------------------------------------------------
# Validate params
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_params_valid():
    """POST /skeletons/validate-params with valid params returns valid=true."""
    async with httpx.AsyncClient() as client:
        project_id = await _get_project_id(client)
        if not project_id:
            pytest.skip("No projects exist — run seed script first")

        resp = await client.post(
            f"{BASE}/{project_id}/skeletons/validate-params",
            json={
                "template_id": "aws_ec2",
                "params": VALID_PARAMS["aws_ec2"],
            },
        )
        assert resp.status_code == 200, (
            f"Validate params failed with {resp.status_code}: {resp.text}"
        )
        data = resp.json()
        assert data["valid"] is True, f"Expected valid=true, got {data}"


@pytest.mark.asyncio
async def test_validate_params_invalid():
    """POST /skeletons/validate-params with missing required returns valid=false."""
    async with httpx.AsyncClient() as client:
        project_id = await _get_project_id(client)
        if not project_id:
            pytest.skip("No projects exist — run seed script first")

        resp = await client.post(
            f"{BASE}/{project_id}/skeletons/validate-params",
            json={
                "template_id": "aws_ec2",
                "params": {},  # no required fields
            },
        )
        assert resp.status_code == 200, (
            f"Validate params failed with {resp.status_code}: {resp.text}"
        )
        data = resp.json()
        assert data["valid"] is False, f"Expected valid=false, got {data}"
        assert "errors" in data, "Missing 'errors' in validation response"
        assert len(data["errors"]) > 0, (
            f"Expected non-empty errors list, got {data['errors']}"
        )


# ---------------------------------------------------------------------------
# Scaffold history
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scaffold_history():
    """GET /skeletons/history returns items and total."""
    async with httpx.AsyncClient() as client:
        project_id = await _get_project_id(client)
        if not project_id:
            pytest.skip("No projects exist — run seed script first")

        resp = await client.get(f"{BASE}/{project_id}/skeletons/history")
        assert resp.status_code == 200, (
            f"History failed with {resp.status_code}: {resp.text}"
        )
        data = resp.json()
        assert "items" in data, "Missing 'items' in history response"
        assert "total" in data, "Missing 'total' in history response"
        assert isinstance(data["items"], list)
        assert isinstance(data["total"], int)