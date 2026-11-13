from __future__ import annotations

import os
import sys
from pathlib import Path

_TEST_DB_PATH = Path(__file__).resolve().parent / ".test_privacy_gateway.db"
os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB_PATH.as_posix()}"
os.environ["REDIS_URL"] = "memory://"
os.environ["JWT_SECRET"] = "test-jwt-secret-key-with-more-than-32-characters"
os.environ["MAPPING_ENCRYPTION_KEY"] = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
os.environ["ALLOWED_PROVIDERS"] = "gemini,openai,local_slm"
os.environ["DEFAULT_LLM_PROVIDER"] = "gemini"

BACKEND_DIR = Path(__file__).resolve().parents[1]
VENDOR_DIR = BACKEND_DIR / ".vendor"
if VENDOR_DIR.is_dir() and str(VENDOR_DIR) not in sys.path:
    sys.path.insert(0, str(VENDOR_DIR))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import fakeredis  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.database.session import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.services.auth_service import ensure_seed_data  # noqa: E402
from app.services.llm.base import BaseLLMProvider, LLMGenerationResult  # noqa: E402
from app.services.llm.orchestrator import get_llm_orchestrator  # noqa: E402
from app.services.privacy_vault.vault import PrivacyVault, set_privacy_vault  # noqa: E402


class StubTestLLMProvider(BaseLLMProvider):
    """Test-only adapter that records outbound payloads and echoes placeholders for deterministic CI tests."""

    def __init__(self, name: str = "gemini") -> None:
        self.name = name
        self.called_count = 0
        self.last_payload = None
        self.next_response_fn = None

    def is_configured(self) -> bool:
        return True

    def default_model(self) -> str:
        return "gemini-3.8-flash" if self.name == "gemini" else "gpt-4o-mini"

    async def generate(self, payload):
        self.called_count += 1
        self.last_payload = payload
        if self.next_response_fn is not None:
            content = self.next_response_fn(payload)
        else:
            content = f"Processed summary for sanitized input:\n{payload.user_prompt}"
        return LLMGenerationResult(
            provider=self.name,
            model=payload.model or self.default_model(),
            content=content,
            latency_ms=12.5,
            prompt_tokens=40,
            completion_tokens=25,
        )


@pytest.fixture(autouse=True)
def reset_test_state():
    get_settings.cache_clear()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        ensure_seed_data(db)

    fake_redis = fakeredis.FakeRedis(decode_responses=False)
    vault = PrivacyVault(redis_client=fake_redis)
    set_privacy_vault(vault)
    yield fake_redis
    set_privacy_vault(None)


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_db():
    yield
    engine.dispose()
    if _TEST_DB_PATH.exists():
        try:
            _TEST_DB_PATH.unlink()
        except OSError:
            pass


@pytest.fixture
def client():
    with TestClient(app) as tc:
        yield tc


@pytest.fixture
def stub_gemini():
    stub = StubTestLLMProvider("gemini")
    orch = get_llm_orchestrator()
    orig = orch._providers.get("gemini")
    orch.register_provider(stub)
    yield stub
    if orig is not None:
        orch.register_provider(orig)
