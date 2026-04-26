"""관리자용 regulation_document CRUD 및 rechunk API를 제공하는 라우터 파일입니다."""

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Path
from fastapi import status
from sqlalchemy.orm import Session

from app.api.dependencies.admin_auth import require_admin_token
from app.db.session import get_db
from app.schemas.common import ApiResponse
from app.schemas.regulation_document import RegulationDocumentCommandResult
from app.schemas.regulation_document import RegulationDocumentBulkCreateRequest
from app.schemas.regulation_document import RegulationDocumentBulkCreateResult
from app.schemas.regulation_document import RegulationDocumentCreateRequest
from app.schemas.regulation_document import RegulationDocumentUpdateRequest
from app.services.regulation_document_service import create_regulation_documents_with_ingestion
from app.services.regulation_document_service import create_regulation_document_with_ingestion
from app.services.regulation_document_service import delete_regulation_document
from app.services.regulation_document_service import rechunk_regulation_document
from app.services.regulation_document_service import update_regulation_document_with_ingestion

router = APIRouter(
    prefix="/admin/regulations",
    tags=["admin-regulation-documents"],
    dependencies=[Depends(require_admin_token)],
)


@router.post(
    "",
    response_model=ApiResponse[RegulationDocumentCommandResult],
    status_code=status.HTTP_201_CREATED,
    summary="규정 문서 생성 및 자동 청킹",
    description=(
        "새 regulation_document를 생성한 뒤 같은 요청 안에서 자동으로 청킹과 embedding 적재를 시도합니다.\n\n"
        "이 API는 원문 문서를 등록하는 API입니다.\n"
        "- 문서 row를 새로 만듭니다.\n"
        "- 성공 시 새 문서 버전을 활성화합니다.\n"
        "- 자동 적재가 실패해도 문서 생성 자체는 성공할 수 있으며, 이 경우 `ingestion_status`와 "
        "`ingestion_error_code`로 후속 조치가 필요한지 판단할 수 있습니다."
    ),
)
def create_regulation_document_admin_api(
    payload: RegulationDocumentCreateRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[RegulationDocumentCommandResult]:
    result = create_regulation_document_with_ingestion(db, payload)
    return ApiResponse(
        status=status.HTTP_201_CREATED,
        message="regulation document created",
        data=result,
    )


@router.post(
    "/bulk",
    response_model=ApiResponse[RegulationDocumentBulkCreateResult],
    status_code=status.HTTP_201_CREATED,
    summary="규정 문서 벌크 생성 및 자동 청킹",
    description=(
        "최대 20개의 regulation_document를 한 번에 생성하고, 각 문서마다 자동으로 청킹과 embedding 적재를 시도합니다.\n\n"
        "이 API는 부분 성공을 허용합니다.\n"
        "- 한 문서가 중복이나 검증 문제로 실패해도 다른 문서는 계속 처리합니다.\n"
        "- 각 문서별 성공/실패 상태는 `items[].status`에서 확인할 수 있습니다.\n"
        "- 자동 적재 실패 여부는 각 결과의 `ingestion_status`, `ingestion_error_code`에서 확인합니다."
    ),
)
def create_regulation_documents_bulk_admin_api(
    payload: RegulationDocumentBulkCreateRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[RegulationDocumentBulkCreateResult]:
    result = create_regulation_documents_with_ingestion(db, payload)
    return ApiResponse(
        status=status.HTTP_201_CREATED,
        message="regulation documents processed",
        data=result,
    )


@router.patch(
    "/{regulation_document_id}",
    response_model=ApiResponse[RegulationDocumentCommandResult],
    status_code=status.HTTP_200_OK,
    summary="규정 문서 수정 및 필요 시 재청킹",
    description=(
        "기존 regulation_document의 메타데이터나 본문을 수정합니다.\n\n"
        "본문, 제목, 출처 등 검색 품질에 영향을 주는 필드가 바뀌면 서버가 자동으로 기존 청크를 비활성화하고 "
        "새 청크를 다시 생성합니다. 단순 문서 수정과 재적재를 한 번에 처리하는 API입니다."
    ),
)
def update_regulation_document_admin_api(
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
    description=(
        "문서를 soft delete 처리하고 연결된 활성 청크를 함께 비활성화합니다.\n\n"
        "문서와 청크를 물리 삭제하지 않고 검색 대상에서만 제외하므로, 운영 추적과 이력 확인이 가능합니다."
    ),
)
def delete_regulation_document_admin_api(
    regulation_document_id: int = Path(ge=1),
    db: Session = Depends(get_db),
) -> ApiResponse[RegulationDocumentCommandResult]:
    result = delete_regulation_document(db, regulation_document_id)
    return ApiResponse(
        status=status.HTTP_200_OK,
        message="regulation document deleted",
        data=result,
    )


@router.post(
    "/{regulation_document_id}/rechunk",
    response_model=ApiResponse[RegulationDocumentCommandResult],
    status_code=status.HTTP_200_OK,
    summary="규정 문서 청크 강제 재생성",
    description=(
        "이미 존재하는 regulation_document를 기준으로 기존 활성 청크를 비활성화하고 새 청크와 embedding을 다시 생성합니다.\n\n"
        "`POST /admin/regulation-chunks`와의 차이:\n"
        "- `POST /admin/regulation-chunks`: 아직 청크가 없는 문서의 최초 적재용입니다. 이미 청크가 있으면 409를 반환합니다.\n"
        "- `POST /admin/regulations/{regulation_document_id}/rechunk`: 기존 청크가 있어도 강제로 다시 생성합니다. "
        "청킹 규칙 변경, 임베딩 모델 교체, 품질 보정이 필요할 때 사용합니다.\n\n"
        "즉, `regulation-chunks`는 초기 적재, `rechunk`는 교체 재적재용 API입니다."
    ),
)
def rechunk_regulation_document_admin_api(
    regulation_document_id: int = Path(ge=1),
    db: Session = Depends(get_db),
) -> ApiResponse[RegulationDocumentCommandResult]:
    result = rechunk_regulation_document(db, regulation_document_id)
    return ApiResponse(
        status=status.HTTP_200_OK,
        message="regulation document rechunked",
        data=result,
    )
