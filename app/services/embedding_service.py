"""외부 OpenAI 임베딩 API 호출을 한 곳에 모아둔 서비스 파일입니다."""

from typing import Any
from typing import Optional

import httpx

from app.core.config import get_settings
from app.core.error_codes import EMBEDDING_DIMENSION_MISMATCH
from app.core.error_codes import EMBEDDING_GENERATION_FAILED
from app.core.error_codes import INVALID_EMBEDDING_RESPONSE
from app.core.error_codes import OPENAI_API_ERROR
from app.core.error_codes import OPENAI_API_KEY_MISSING
from app.core.error_codes import OPENAI_API_TIMEOUT
from app.core.exceptions import AppException


def create_embedding(text: str, client: Optional[httpx.Client] = None) -> list[float]:
    """주어진 텍스트를 OpenAI 임베딩으로 변환하고 벡터 길이까지 검증합니다."""

    return create_embeddings_batch([text], client=client)[0]


def create_embeddings_batch(
    texts: list[str],
    client: Optional[httpx.Client] = None,
) -> list[list[float]]:
    """여러 텍스트를 한 번의 OpenAI 호출로 임베딩해 배치 적재 성능을 높입니다."""

    settings = get_settings()
    if not settings.openai_api_key:
        raise AppException(OPENAI_API_KEY_MISSING)

    if not texts:
        return []

    payload = {
        "input": texts,
        "model": settings.openai_embedding_model,
        "dimensions": settings.openai_embedding_dimension,
    }

    should_close_client = client is None
    http_client = client or httpx.Client(timeout=settings.openai_timeout_seconds)

    try:
        response = http_client.post(
            "https://api.openai.com/v1/embeddings",
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        try:
            response_payload = response.json()
        except ValueError as exc:
            raise AppException(INVALID_EMBEDDING_RESPONSE) from exc

        return _parse_embeddings_response(response_payload, settings.openai_embedding_dimension)
    except httpx.TimeoutException as exc:
        raise AppException(OPENAI_API_TIMEOUT) from exc
    except httpx.HTTPStatusError as exc:
        raise AppException(OPENAI_API_ERROR, detail=_extract_http_error_message(exc.response)) from exc
    except httpx.HTTPError as exc:
        raise AppException(EMBEDDING_GENERATION_FAILED) from exc
    finally:
        if should_close_client:
            http_client.close()


def _parse_embeddings_response(payload: dict[str, Any], expected_dimension: int) -> list[list[float]]:
    """OpenAI 응답 JSON에서 임베딩 배열 목록을 꺼내고 형식을 검증합니다."""

    data = payload.get("data")
    if not isinstance(data, list) or not data:
        raise AppException(INVALID_EMBEDDING_RESPONSE)

    embeddings: list[list[float]] = []
    for item in data:
        if not isinstance(item, dict):
            raise AppException(INVALID_EMBEDDING_RESPONSE)

        embedding = item.get("embedding")
        if not isinstance(embedding, list) or not embedding:
            raise AppException(INVALID_EMBEDDING_RESPONSE)

        if len(embedding) != expected_dimension:
            raise AppException(EMBEDDING_DIMENSION_MISMATCH)

        try:
            embeddings.append([float(value) for value in embedding])
        except (TypeError, ValueError) as exc:
            raise AppException(INVALID_EMBEDDING_RESPONSE) from exc

    return embeddings


def _extract_http_error_message(response: httpx.Response) -> str:
    """OpenAI 오류 응답에서 사용자에게 보여줄 메시지를 추출합니다."""

    try:
        payload = response.json()
    except ValueError:
        return OPENAI_API_ERROR.message

    error = payload.get("error")
    if isinstance(error, dict):
        message = error.get("message")
        if isinstance(message, str) and message:
            return message

    return OPENAI_API_ERROR.message
