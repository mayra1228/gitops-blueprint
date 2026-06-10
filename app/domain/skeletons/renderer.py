import logging
import re

from app.domain.skeletons.models import SkeletonPreview, SkeletonTemplate

logger = logging.getLogger(__name__)


class TemplateRenderer:
    """Renders skeleton directory trees with {{var}} interpolation.

    Supports both YAML and HCL output modes. The rendering engine is
    identical for both — the template content determines the output format.
    """

    def render_tree(self, template: SkeletonTemplate, params: dict) -> SkeletonPreview:
        rendered = []
        for directory in template.directories:
            dir_path = self._render_string(directory.path_template, params)
            for sf in directory.files:
                filename = self._render_string(sf.filename_template, params)
                content = self._render_string(sf.content_template, params)
                rendered.append({
                    "path": f"{dir_path}/{filename}",
                    "directory": dir_path,
                    "filename": filename,
                    "content": content,
                    "file_type": sf.file_type,
                })

        logger.info("Rendered %d files in %d directories for template %s",
                     len(rendered), len(template.directories), template.id)
        return SkeletonPreview(files=rendered)

    def _render_string(self, text: str, params: dict) -> str:
        # {{var or 'default'}}
        result = re.sub(
            r"\{\{\s*(\w+)\s+or\s+'([^']*)'\s*\}\}",
            lambda m: str(params.get(m.group(1), m.group(2))),
            text,
        )
        # {{var}}  —  empty string if not provided
        result = re.sub(
            r'\{\{\s*(\w+)\s*\}\}',
            lambda m: str(params.get(m.group(1), "")),
            result,
        )
        return result
