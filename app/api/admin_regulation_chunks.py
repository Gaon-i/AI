"""관리자용 regulation_chunk 생성 API를 제공하는 라우터 파일입니다."""

from fastapi import APIRouter
from fastapi import Depends
from fastapi import status
from sqlalchemy.orm import Session

from app.api.dependencies.admin_auth import require_admin_token
from app.db.session import get_db
from app.schemas.common import ApiResponse
from app.schemas.regulation_chunk import RegulationChunkBulkCreateRequest
from app.schemas.regulation_chunk import RegulationChunkBulkCreateResult
from app.schemas.regulation_chunk import RegulationChunkCreateRequest
from app.schemas.regulation_chunk import RegulationChunkCreateResult
from app.services.regulation_chunk_service import create_regulation_chunks_with_embeddings
from app.services.regulation_chunk_service import create_regulation_chunk_with_embedding

router = APIRouter(
    prefix="/admin/regulation-chunks",
    tags=["admin-regulation-chunks"],
    dependencies=[Depends(require_admin_token)],
)


@router.post(
    "",
    response_model=ApiResponse[RegulationChunkCreateResult],
    status_code=status.HTTP_201_CREATED,
    summary="규정 청크 단건 생성",
    description=(
        "관리자 또는 적재 스크립트가 regulation_chunk 데이터를 보내면 "
        "서버가 chunk_text와 embedding을 생성한 뒤 DB에 저장합니다."
    ),
    response_description="청크가 정상 생성되면 생성된 regulation_chunk 정보를 반환합니다.",
)
def create_regulation_chunk_api(
    payload: RegulationChunkCreateRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[RegulationChunkCreateResult]:
    """단건 청크 생성 요청을 service 계층에 위임하고 공통 응답으로 감싸 반환합니다."""

    result = create_regulation_chunk_with_embedding(db, payload)
    return ApiResponse(
        status=status.HTTP_201_CREATED,
        message="regulation chunk created",
        data=result,
    )


@router.post(
    "/bulk",
    response_model=ApiResponse[RegulationChunkBulkCreateResult],
    status_code=status.HTTP_201_CREATED,
    summary="규정 청크 벌크 생성",
    description=(
        "최대 20개의 regulation_chunk를 한 번에 적재합니다. "
        "하나라도 실패하면 전체 요청을 rollback 합니다."
    ),
    response_description="모든 청크가 정상 생성되면 생성 건수와 각 청크 상태를 반환합니다.",
)
def create_regulation_chunks_bulk_api(
    payload: RegulationChunkBulkCreateRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[RegulationChunkBulkCreateResult]:
    """벌크 청크 생성 요청을 service 계층에 위임하고 공통 응답으로 감싸 반환합니다."""

    result = create_regulation_chunks_with_embeddings(db, payload)
    return ApiResponse(
        status=status.HTTP_201_CREATED,
        message="regulation chunks created",
        data=result,
    )
