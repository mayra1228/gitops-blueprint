"""Tests for the import flow: TerraformFileScanner, URL parsing, and import API.

Usage:
    python3 -m pytest tests/test_imports.py -v
"""

import tempfile
from pathlib import Path

import pytest

from app.domain.imports.service import parse_repo_url, DiscoverResult
from app.domain.inventory.terraform_scanner import TerraformFileScanner


# ---------------------------------------------------------------------------
# URL parsing
# ---------------------------------------------------------------------------


def test_parse_github_url():
    result = parse_repo_url("https://github.com/my-org/terraform-infra")
    assert result["org"] == "my-org"
    assert result["repo"] == "terraform-infra"
    assert result["provider"] == "github"


def test_parse_github_url_with_git_suffix():
    result = parse_repo_url("https://github.com/my-org/terraform-infra.git")
    assert result["org"] == "my-org"
    assert result["repo"] == "terraform-infra"


def test_parse_gitlab_url():
    result = parse_repo_url("https://gitlab.com/my-org/terraform-infra")
    assert result["org"] == "my-org"
    assert result["repo"] == "terraform-infra"
    assert result["provider"] == "gitlab"


def test_parse_bitbucket_url():
    result = parse_repo_url("https://bitbucket.org/my-org/terraform-infra")
    assert result["org"] == "my-org"
    assert result["repo"] == "terraform-infra"
    assert result["provider"] == "bitbucket"


def test_parse_url_with_explicit_provider():
    result = parse_repo_url("https://custom-git.com/org/repo", provider="github")
    assert result["org"] == "org"
    assert result["repo"] == "repo"
    assert result["provider"] == "github"


def test_parse_invalid_url():
    with pytest.raises(ValueError, match="Unable to parse repo URL"):
        parse_repo_url("not-a-url")


# ---------------------------------------------------------------------------
# TerraformFileScanner
# ---------------------------------------------------------------------------


def _make_tf_file(root: Path, rel_path: str, content: str) -> Path:
    p = root / rel_path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return p


def test_scan_empty_directory():
    with tempfile.TemporaryDirectory() as tmp:
        scanner = TerraformFileScanner()
        result = scanner.scan(tmp)
        assert result.status == "success"
        assert result.summary["total_files"] == 0
        assert result.summary["total_resources"] == 0
        assert len(result.files) == 0
        assert len(result.errors) == 0


def test_scan_no_tf_files():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "README.md").write_text("# Hello")
        (root / "config.yaml").write_text("key: value")
        scanner = TerraformFileScanner()
        result = scanner.scan(root)
        assert result.status == "success"
        assert result.summary["total_files"] == 0


def test_scan_single_resource():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _make_tf_file(root, "main.tf", """
resource "aws_instance" "web" {
  ami = "ami-123"
  instance_type = "t3.micro"
}
""")
        scanner = TerraformFileScanner()
        result = scanner.scan(root)
        assert result.status == "success"
        assert result.summary["total_files"] == 1
        assert result.summary["total_resources"] == 1
        assert result.summary["resource_types"] == {"aws_instance": 1}
        assert result.files[0].resources == [{"type": "aws_instance", "name": "web"}]


def test_scan_multiple_resources():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _make_tf_file(root, "main.tf", """
resource "aws_instance" "web" {}
resource "aws_s3_bucket" "logs" {}
resource "aws_instance" "worker" {}
""")
        scanner = TerraformFileScanner()
        result = scanner.scan(root)
        assert result.summary["total_resources"] == 3
        assert result.summary["resource_types"] == {"aws_instance": 2, "aws_s3_bucket": 1}


def test_scan_module_and_provider():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _make_tf_file(root, "main.tf", """
provider "aws" {
  region = "us-east-1"
}

module "vpc" {
  source = "terraform-aws-modules/vpc/aws"
}

provider "kubernetes" {}
""")
        scanner = TerraformFileScanner()
        result = scanner.scan(root)
        assert result.summary["total_modules"] == 1
        assert result.summary["providers"] == ["aws", "kubernetes"]
        assert result.files[0].modules[0]["name"] == "vpc"
        assert result.files[0].modules[0]["source"] == "terraform-aws-modules/vpc/aws"


def test_scan_variables_and_outputs():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _make_tf_file(root, "variables.tf", """
variable "instance_type" {
  default = "t3.micro"
}

variable "env" {
  default = "prod"
}

output "instance_ip" {
  value = "10.0.0.1"
}
""")
        scanner = TerraformFileScanner()
        result = scanner.scan(root)
        assert result.summary["total_variables"] == 2
        assert result.summary["total_outputs"] == 1
        assert {"name": "instance_type", "default": "t3.micro"} in result.files[0].variables
        assert {"name": "env", "default": "prod"} in result.files[0].variables
        assert {"name": "instance_ip"} in result.files[0].outputs


def test_scan_nested_directories():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _make_tf_file(root, "infra/aws/ec2/main.tf", 'resource "aws_instance" "web" {}')
        _make_tf_file(root, "infra/aws/rds/main.tf", 'resource "aws_db_instance" "db" {}')
        _make_tf_file(root, "infra/k8s/main.tf", 'resource "kubernetes_deployment" "app" {}')
        scanner = TerraformFileScanner()
        result = scanner.scan(root)
        assert result.summary["total_files"] == 3
        assert result.summary["total_resources"] == 3
        paths = {f.path for f in result.files}
        assert "infra/aws/ec2/main.tf" in paths
        assert "infra/aws/rds/main.tf" in paths
        assert "infra/k8s/main.tf" in paths


def test_scan_malformed_tf_does_not_crash():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _make_tf_file(root, "broken.tf", "this is not valid {{{ hcl")
        scanner = TerraformFileScanner()
        result = scanner.scan(root)
        # Should not crash; malformed .tf files produce no structured data
        assert result.errors == []
        assert result.summary["total_files"] == 0 or result.summary["total_resources"] == 0


def test_scan_to_dict():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _make_tf_file(root, "main.tf", 'resource "aws_instance" "web" {}')
        scanner = TerraformFileScanner()
        result = scanner.scan(root)
        d = result.to_dict()
        assert d["status"] == "success"
        assert isinstance(d["files"], list)
        assert len(d["files"]) == 1
        assert d["files"][0]["path"] == "main.tf"
        assert d["summary"]["total_resources"] == 1


def test_discover_result_to_dict():
    result = DiscoverResult(
        status="success",
        repo={"org": "test", "repo": "test-repo"},
        summary={"total_files": 5, "terraform_files": 3},
    )
    d = result.to_dict()
    assert d["status"] == "success"
    assert d["repo"]["org"] == "test"
    assert d["summary"]["total_files"] == 5