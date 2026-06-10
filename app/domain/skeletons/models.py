from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class SkeletonFile:
    filename_template: str
    content_template: str
    file_type: str = "text"


@dataclass
class SkeletonDirectory:
    path_template: str
    files: List[SkeletonFile] = field(default_factory=list)


@dataclass
class SkeletonTemplate:
    id: str
    name: str
    provider: str
    render_mode: str  # "yaml" | "hcl"
    capability_id: str
    description: str = ""
    parameter_schema: Dict[str, object] = field(default_factory=dict)
    directories: List[SkeletonDirectory] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    linked_template_id: Optional[str] = None

    def to_dict(self) -> Dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "provider": self.provider,
            "render_mode": self.render_mode,
            "capability_id": self.capability_id,
            "description": self.description,
            "parameter_schema": dict(self.parameter_schema),
            "directory_count": len(self.directories),
            "file_count": sum(len(d.files) for d in self.directories),
            "directories": [
                {
                    "path_template": d.path_template,
                    "files": [
                        {"filename_template": f.filename_template, "file_type": f.file_type}
                        for f in d.files
                    ],
                }
                for d in self.directories
            ],
            "tags": list(self.tags),
            "linked_template_id": self.linked_template_id,
        }


@dataclass
class SkeletonPreview:
    files: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class SkeletonResult:
    success: bool
    preview: Optional[SkeletonPreview] = None
    pr_url: Optional[str] = None
    branch: Optional[str] = None
    commit_sha: Optional[str] = None
    capability_id: Optional[str] = None
    error: Optional[str] = None


@dataclass
class ParameterValidationResult:
    valid: bool
    errors: List[Dict[str, str]] = field(default_factory=list)
