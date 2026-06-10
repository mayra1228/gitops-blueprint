from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://gitops:gitops_dev@localhost:5432/gitops_platform"
    database_url_sync: str = "postgresql://gitops:gitops_dev@localhost:5432/gitops_platform"
    jwt_secret: str = "dev-secret-change-in-production"
    github_token: str = ""
    github_webhook_secret: str = "dev-webhook-secret"
    bitbucket_username: str = ""
    bitbucket_app_password: str = ""
    bitbucket_webhook_secret: str = "dev-webhook-secret"
    gitlab_token: str = ""
    gitlab_webhook_secret: str = "dev-webhook-secret"
    demo_data_root: str = "/demo_data"
    repo_storage_root: str = "/data/repos"
    kubeconfig_path: str = ""
    k8s_context: str = ""
    k8s_execution_mode: str = "sandbox"
    k8s_namespace_allowlist: str = ""
    k8s_allowed_cluster: str = "kind-gitops-sandbox"

    @property
    def allowed_namespaces(self) -> list[str]:
        if not self.k8s_namespace_allowlist:
            return []
        return [ns.strip() for ns in self.k8s_namespace_allowlist.split(",") if ns.strip()]

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
