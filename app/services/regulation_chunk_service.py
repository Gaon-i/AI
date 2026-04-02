"""청크 생성 비즈니스 흐름을 조합하는 서비스 파일입니다."""

from sqlalchemy.orm import Session

from app.core.error_codes import INVALID_CHUNK_TEXT
from app.core.error_codes import REGULATION_CHUNK_ALREADY_EXISTS
from app.core.error_codes import REGULATION_CHUNK_CREATE_FAILED
from app.core.exceptions import AppException
from app.repositories.regulation_chunk_repository import create_regulation_chunk
from app.repositories.regulation_chunk_repository import find_by_chunk_id
from app.schemas.regulation_chunk import RegulationChunkCreateRequest
from app.schemas.regulation_chunk import RegulationChunkCreateResult
from app.services.embedding_service import create_embedding


def create_regulation_chunk_with_embedding(
    db: Session,
    payload: RegulationChunkCreateRequest,
) -> RegulationChunkCreateResult:
    """중복 확인부터 임베딩 생성, DB 저장, 결과 반환까지 한 번에 처리합니다."""

    try:
        if find_by_chunk_id(db, payload.chunk_id) is not None:
            raise AppException(REGULATION_CHUNK_ALREADY_EXISTS)

        chunk_text = build_chunk_text(payload)
        if not chunk_text.strip():
            raise AppException(INVALID_CHUNK_TEXT)

        embedding = create_embedding(chunk_text)

        regulation_chunk = create_regulation_chunk(
            db=db,
            payload=payload,
            chunk_text=chunk_text,
            embedding=embedding,
        )
        db.commit()
    except AppException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise AppException(REGULATION_CHUNK_CREATE_FAILED) from exc

    return RegulationChunkCreateResult(
        regulation_chunk_id=regulation_chunk.regulation_chunk_id,
        document_id=regulation_chunk.document_id,
        chunk_id=regulation_chunk.chunk_id,
        chunk_index=regulation_chunk.chunk_index,
        source_type=payload.source_type,
    )


def build_chunk_text(payload: RegulationChunkCreateRequest) -> str:
    """검색 품질이 일정하도록 구조화된 필드를 임베딩용 문자열로 합칩니다."""

    parts: list[str] = []

    # document_id는 검색용 의미 텍스트보다 원본 추적/그룹핑 용도에 가깝기 때문에 임베딩 본문엔 넣지 않습니다.
    if payload.dormitory:
        parts.append(f"생활관: {payload.dormitory}")
    if payload.category:
        parts.append(f"카테고리: {payload.category}")

    parts.append(f"제목: {payload.title}")
    parts.append(f"본문: {payload.content}")

    if payload.keywords:
        parts.append(f"키워드: {', '.join(payload.keywords)}")
    if payload.source:
        parts.append(f"출처: {payload.source}")
    if payload.source_url:
        parts.append(f"출처 URL: {payload.source_url}")

    parts.append(f"출처유형: {payload.source_type.value}")

    return "\n".join(parts)
