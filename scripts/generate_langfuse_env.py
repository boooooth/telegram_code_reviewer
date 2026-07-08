"""Generate docker/langfuse/.env with random secrets and an auto-provisioned
Langfuse org/project/admin user, so `docker compose up -d` produces a ready-to-use
instance with no manual signup through the web UI.

Usage:
    .venv\\Scripts\\python.exe scripts\\generate_langfuse_env.py
    .venv\\Scripts\\python.exe scripts\\generate_langfuse_env.py --force  # overwrite existing .env
"""

import argparse
import secrets
from pathlib import Path

ENV_PATH = Path(__file__).resolve().parents[1] / "docker" / "langfuse" / ".env"


def generate() -> dict[str, str]:
    postgres_password = secrets.token_urlsafe(24)
    minio_password = secrets.token_urlsafe(24)

    return {
        "SALT": secrets.token_hex(16),
        "ENCRYPTION_KEY": secrets.token_hex(32),
        "NEXTAUTH_SECRET": secrets.token_urlsafe(32),
        "POSTGRES_PASSWORD": postgres_password,
        "CLICKHOUSE_PASSWORD": secrets.token_urlsafe(24),
        "REDIS_AUTH": secrets.token_urlsafe(24),
        "MINIO_ROOT_PASSWORD": minio_password,
        "DATABASE_URL": f"postgresql://postgres:{postgres_password}@postgres:5432/postgres",
        "LANGFUSE_S3_EVENT_UPLOAD_SECRET_ACCESS_KEY": minio_password,
        "LANGFUSE_S3_MEDIA_UPLOAD_SECRET_ACCESS_KEY": minio_password,
        "LANGFUSE_S3_BATCH_EXPORT_SECRET_ACCESS_KEY": minio_password,
        # Auto-provision an org/project/admin user on first boot, skipping the
        # browser signup flow. See https://langfuse.com/self-hosting/configuration
        "LANGFUSE_INIT_ORG_ID": "reviewbot-org",
        "LANGFUSE_INIT_ORG_NAME": "Review Bot",
        "LANGFUSE_INIT_PROJECT_ID": "reviewbot-project",
        "LANGFUSE_INIT_PROJECT_NAME": "Review Bot",
        "LANGFUSE_INIT_PROJECT_PUBLIC_KEY": f"pk-lf-{secrets.token_hex(16)}",
        "LANGFUSE_INIT_PROJECT_SECRET_KEY": f"sk-lf-{secrets.token_hex(16)}",
        "LANGFUSE_INIT_USER_EMAIL": "admin@reviewbot.local",
        "LANGFUSE_INIT_USER_NAME": "Admin",
        "LANGFUSE_INIT_USER_PASSWORD": secrets.token_urlsafe(18),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="overwrite an existing .env")
    args = parser.parse_args()

    if ENV_PATH.exists() and not args.force:
        raise SystemExit(f"{ENV_PATH} already exists. Re-run with --force to overwrite it.")

    values = generate()
    ENV_PATH.parent.mkdir(parents=True, exist_ok=True)
    ENV_PATH.write_text("".join(f"{key}={value}\n" for key, value in values.items()), encoding="utf-8")

    print(f"Wrote {ENV_PATH}\n")
    print("Now run:")
    print("  cd docker/langfuse && docker compose up -d")
    print("\nOnce it's up, copy these into your project's .env:")
    print(f"  LANGFUSE_PUBLIC_KEY={values['LANGFUSE_INIT_PROJECT_PUBLIC_KEY']}")
    print(f"  LANGFUSE_SECRET_KEY={values['LANGFUSE_INIT_PROJECT_SECRET_KEY']}")
    print("  LANGFUSE_HOST=http://localhost:3000")
    print(f"\nLangfuse admin login: {values['LANGFUSE_INIT_USER_EMAIL']} / {values['LANGFUSE_INIT_USER_PASSWORD']}")


if __name__ == "__main__":
    main()
