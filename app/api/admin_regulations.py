"""관리자용 regulation_document CRUD API를 제공하는 라우터 파일입니다."""

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Path
from fastapi import status
from sqlalchemy.orm import Session

from app.api.dependencies.admin_auth import require_admin_token
from app.db.session import get_db
from app.schemas.common import ApiResponse
from app.schemas.regulation_document import RegulationDocumentCommandResult
from app.schemas.regulation_document import RegulationDocumentCreateRequest
from app.schemas.regulation_document import RegulationDocumentUpdateRequest
from app.services.regulation_document_service import create_regulation_document_with_ingestion
from app.services.regulation_document_service import delete_regulation_document
from app.services.regulation_document_service import update_regulation_document_with_ingestion

router = APIRouter(
    prefix="/admin/regulations",
    tags=["admin-regulations"],
    dependencies=[Depends(require_admin_token)],
)


@router.post(
    "",
    response_model=ApiResponse[RegulationDocumentCommandResult],
    status_code=status.HTTP_201_CREATED,
    summary="규정 문서 생성 및 자동 청킹",
)
def create_regulation_document_api(
    payload: RegulationDocumentCreateRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[RegulationDocumentCommandResult]:
    result = create_regulation_document_with_ingestion(db, payload)
    return ApiResponse(
        status=status.HTTP_201_CREATED,
        message="regulation document created",
        data=result,
    )


@router.patch(
    "/{regulation_document_id}",
    response_model=ApiResponse[RegulationDocumentCommandResult],
    status_code=status.HTTP_200_OK,
    summary="규정 문서 수정 및 필요 시 재청킹",
)
def update_regulation_document_api(
    payload: RegulationDocumentUpdateRequest,
    regulation_document_id: int = Path(ge=1),
    db: Session = Depends(get_db),
) -> ApiResponse[RegulationDocumentCommandResult]:
    result = update_regulation_document_with_ingestion(db, regulation_document_id, payload)
    return ApiResponse(
        status=status.HTTP_200_OK,
        message="regulation document updated",
        data=result,
    )


@router.delete(
    "/{regulation_document_id}",
    response_model=ApiResponse[RegulationDocumentCommandResult],
    status_code=status.HTTP_200_OK,
    summary="규정 문서 삭제 및 청크 비활성화",
)
def delete_regulation_document_api(
    regulation_document_id: int = Path(ge=1),
    db: Session = Depends(get_db),
) -> ApiResponse[RegulationDocumentCommandResult]:
    result = delete_regulation_document(db, regulation_document_id)
    return ApiResponse(
        status=status.HTTP_200_OK,
        message="regulation document deleted",
        data=result,
    )
