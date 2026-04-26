"""관리자용 regulation_chunk 최초 적재 API를 제공하는 라우터 파일입니다."""

from fastapi import APIRouter
from fastapi import Depends
from fastapi import status
from sqlalchemy.orm import Session

from app.api.dependencies.admin_auth import require_admin_token
from app.db.session import get_db
from app.schemas.common import ApiResponse
from app.schemas.regulation_chunk import RegulationChunkBulkIngestionRequest
from app.schemas.regulation_chunk import RegulationChunkBulkIngestionResult
from app.schemas.regulation_chunk import RegulationChunkIngestionRequest
from app.schemas.regulation_chunk import RegulationChunkIngestionResult
from app.services.regulation_chunk_service import ingest_regulation_chunks_for_document
from app.services.regulation_chunk_service import ingest_regulation_chunks_for_documents

router = APIRouter(
    prefix="/admin/regulation-chunks",
    tags=["admin-regulation-chunk-ingestion"],
    dependencies=[Depends(require_admin_token)],
)


@router.post(
    "",
    response_model=ApiResponse[RegulationChunkIngestionResult],
    status_code=status.HTTP_201_CREATED,
    summary="규정 문서 최초 청크 적재",
    description=(
        "내부 운영/복구용 API입니다. 일반적인 흐름에서는 관리자가 직접 호출하지 않고 "
        "`POST /api/v1/admin/regulations` 호출 시 서버 내부에서 자동으로 사용됩니다.\n\n"
        "이 API는 `아직 청크가 없는 문서`의 최초 적재 또는 자동 적재 실패 후 수동 복구용입니다.\n"
        "- 이미 해당 문서에 청크가 있으면 409 `REGULATION_CHUNK_ALREADY_EXISTS`를 반환합니다.\n"
        "- 기존 청크를 교체하고 싶다면 이 API가 아니라 "
        "`POST /admin/regulations/{regulation_document_id}/rechunk`를 사용해야 합니다.\n\n"
        "즉, 이 API는 초기 적재 전용이고 재생성 목적에는 쓰지 않습니다."
    ),
    response_description="청크가 정상 생성되면 문서 기준 생성 결과를 반환합니다.",
)
def ingest_regulation_chunks_from_document_admin_api(
    payload: RegulationChunkIngestionRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[RegulationChunkIngestionResult]:
    """단건 문서 기준 청크 적재 요청을 service 계층에 위임하고 공통 응답으로 감싸 반환합니다."""

    result = ingest_regulation_chunks_for_document(db, payload)
    return ApiResponse(
        status=status.HTTP_201_CREATED,
        message="regulation chunks created from document",
        data=result,
    )


@router.post(
    "/bulk",
    response_model=ApiResponse[RegulationChunkBulkIngestionResult],
    status_code=status.HTTP_201_CREATED,
    summary="규정 문서 최초 청크 벌크 적재",
    description=(
        "내부 운영/복구용 벌크 API입니다. 문서 생성 API의 자동 적재 실패로 청크가 비어 있는 문서를 "
        "여러 건 한 번에 복구할 때 사용합니다.\n\n"
        "최대 20개의 regulation_document를 기준으로 최초 청크 적재를 수행합니다. "
        "이 API도 기존 청크가 없는 문서만 대상으로 합니다. "
        "이미 청크가 있는 문서를 다시 생성하려면 각 문서별 `rechunk` API를 사용해야 합니다.\n"
        "하나라도 실패하면 예외를 반환합니다."
    ),
    response_description="모든 문서 청크 적재가 정상 생성되면 생성 건수와 각 문서 상태를 반환합니다.",
)
def ingest_regulation_chunks_from_documents_bulk_admin_api(
    payload: RegulationChunkBulkIngestionRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[RegulationChunkBulkIngestionResult]:
    """벌크 문서 기준 청크 적재 요청을 service 계층에 위임하고 공통 응답으로 감싸 반환합니다."""

    result = ingest_regulation_chunks_for_documents(db, payload)
    return ApiResponse(
        status=status.HTTP_201_CREATED,
        message="regulation chunks created from documents",
        data=result,
    )
