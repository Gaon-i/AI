"""OpenAI 임베딩 연동을 실제 네트워크 없이 검증하는 테스트 파일입니다."""

from typing import Optional

import httpx
import pytest

from app.core.error_codes import EMBEDDING_DIMENSION_MISMATCH
from app.core.error_codes import INVALID_EMBEDDING_RESPONSE
from app.core.error_codes import OPENAI_API_ERROR
from app.core.error_codes import OPENAI_API_KEY_MISSING
from app.core.exceptions import AppException
from app.services.embedding_service import create_embedding
from app.services.embedding_service import create_embeddings_batch


class FakeClient:
    """httpx.Client 대신 주입해 요청 payload와 응답 흐름만 검증하기 위한 테스트 더블입니다."""

    def __init__(self, response: Optional[httpx.Response] = None, exc: Optional[Exception] = None) -> None:
        self.response = response
        self.exc = exc
        self.last_json = None

    def post(self, *args, **kwargs) -> httpx.Response:
        self.last_json = kwargs.get("json")
        if self.exc is not None:
            raise self.exc
        assert self.response is not None
        return self.response


class InvalidJsonResponse:
    """status는 성공이지만 본문 파싱이 실패하는 외부 API 이상 응답을 흉내 냅니다."""

    def raise_for_status(self) -> None:
        return None

    def json(self):
        raise ValueError("invalid json")


def test_create_embedding_raises_when_api_key_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    # 운영 설정 누락은 외부 호출 전에 바로 감지돼야 합니다.
    monkeypatch.setenv("OPENAI_API_KEY", "")

    from app.core.config import get_settings

    get_settings.cache_clear()

    with pytest.raises(AppException) as exc_info:
        create_embedding("생활관: 본관")

    assert exc_info.value.error_code == OPENAI_API_KEY_MISSING


def test_create_embedding_returns_embedding(monkeypatch: pytest.MonkeyPatch) -> None:
    # 정상 응답이면 벡터를 반환하고, OpenAI 요청 payload도 우리가 기대한 형식인지 확인합니다.
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    from app.core.config import get_settings

    get_settings.cache_clear()
    request = httpx.Request("POST", "https://api.openai.com/v1/embeddings")
    response = httpx.Response(
        status_code=200,
        request=request,
        json={"data": [{"embedding": [0.1] * 1536}]},
    )
    client = FakeClient(response=response)

    embedding = create_embedding("생활관: 본관", client=client)

    assert len(embedding) == 1536
    assert embedding[0] == 0.1
    assert client.last_json == {
        "input": ["생활관: 본관"],
        "model": "text-embedding-3-small",
        "dimensions": 1536,
    }


def test_create_embedding_raises_for_dimension_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    # 모델 응답 차원이 DB 스키마와 다르면 저장 전에 바로 실패해야 합니다.
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    from app.core.config import get_settings

    get_settings.cache_clear()
    request = httpx.Request("POST", "https://api.openai.com/v1/embeddings")
    response = httpx.Response(
        status_code=200,
        request=request,
        json={"data": [{"embedding": [0.1, 0.2]}]},
    )

    with pytest.raises(AppException) as exc_info:
        create_embedding("생활관: 본관", client=FakeClient(response=response))

    assert exc_info.value.error_code == EMBEDDING_DIMENSION_MISMATCH


def test_create_embedding_raises_for_http_status_error(monkeypatch: pytest.MonkeyPatch) -> None:
    # OpenAI가 HTTP 에러를 주면 내부 에러 코드와 상세 메시지로 변환되는지 검증합니다.
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    from app.core.config import get_settings

    get_settings.cache_clear()
    request = httpx.Request("POST", "https://api.openai.com/v1/embeddings")
    response = httpx.Response(
        status_code=401,
        request=request,
        json={"error": {"message": "invalid api key"}},
    )

    with pytest.raises(AppException) as exc_info:
        create_embedding(
            "생활관: 본관",
            client=FakeClient(exc=httpx.HTTPStatusError("bad request", request=request, response=response)),
        )

    assert exc_info.value.error_code == OPENAI_API_ERROR
    assert exc_info.value.detail == "invalid api key"


def test_create_embedding_raises_for_invalid_json_response(monkeypatch: pytest.MonkeyPatch) -> None:
    # 200 응답이어도 JSON 본문이 깨져 있으면 유효하지 않은 임베딩 응답으로 처리해야 합니다.
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    from app.core.config import get_settings

    get_settings.cache_clear()

    with pytest.raises(AppException) as exc_info:
        create_embedding("생활관: 본관", client=FakeClient(response=InvalidJsonResponse()))

    assert exc_info.value.error_code == INVALID_EMBEDDING_RESPONSE


def test_create_embeddings_batch_returns_embeddings(monkeypatch: pytest.MonkeyPatch) -> None:
    # 벌크 적재에서는 여러 텍스트를 한 번의 OpenAI 호출로 보내야 합니다.
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    from app.core.config import get_settings

    get_settings.cache_clear()
    request = httpx.Request("POST", "https://api.openai.com/v1/embeddings")
    response = httpx.Response(
        status_code=200,
        request=request,
        json={
            "data": [
                {"embedding": [0.1] * 1536},
                {"embedding": [0.2] * 1536},
            ]
        },
    )
    client = FakeClient(response=response)

    embeddings = create_embeddings_batch(["첫 번째", "두 번째"], client=client)

    assert len(embeddings) == 2
    assert embeddings[0][0] == 0.1
    assert embeddings[1][0] == 0.2
    assert client.last_json == {
        "input": ["첫 번째", "두 번째"],
        "model": "text-embedding-3-small",
        "dimensions": 1536,
    }
