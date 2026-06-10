from pathlib import PurePosixPath


def infer_schema_path(source_path: str):
    parts = PurePosixPath(source_path).parts
    if len(parts) >= 5 and parts[0] == "infra" and parts[1] == "ODP":
        return f"test/schema/ODP/{parts[2]}.yaml"
    if len(parts) >= 6 and parts[0] == "infra" and parts[1] == "aws":
        component = parts[4]
        filename = parts[5]
        return f"test/schema/aws/{component}/{filename}"
    if len(parts) >= 4 and parts[0] == "infra":
        return f"test/schema/{parts[1]}/{parts[2]}.yaml"
    return None
