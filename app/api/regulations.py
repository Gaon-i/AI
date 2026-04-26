from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from fastapi import status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import ApiResponse
from app.schemas.regulation_lookup import RegulationDocumentTypeListResult
from app.schemas.regulation_lookup import RegulationLookupResult
from app.services.regulation_lookup_service import get_regulation_document_types
from app.services.regulation_lookup_service import get_regulation_documents_by_type

router = APIRouter(
    prefix="/regulations",
    tags=["regulations"],
)


@router.get(
    "/document-types",
    response_model=ApiResponse[RegulationDocumentTypeListResult],
    status_code=status.HTTP_200_OK,
    summary="조회 가능한 규정 문서 타입 목록 조회",
)
def get_regulation_document_types_api(
    db: Session = Depends(get_db),
) -> ApiResponse[RegulationDocumentTypeListResult]:
    result = get_regulation_document_types(db)
    return ApiResponse(
        status=status.HTTP_200_OK,
        message="regulation document types retrieved",
        data=result,
    )


@router.get(
    "",
    response_model=ApiResponse[RegulationLookupResult],
    status_code=status.HTTP_200_OK,
    summary="규정 문서 타입 기준 문서 조회",
)
def get_regulation_documents_by_type_api(
    document_type: str = Query(min_length=1, max_length=100),
    db: Session = Depends(get_db),
) -> ApiResponse[RegulationLookupResult]:
    result = get_regulation_documents_by_type(db, document_type)
    return ApiResponse(
        status=status.HTTP_200_OK,
        message="regulation documents retrieved",
        data=result,
    )
