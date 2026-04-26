# Regulation Document Types

`regulation_document.document_id`는 뒤의 숫자 suffix를 제거한 값을 `document_type`으로 취급합니다.

예시:
- `facility_007` -> `facility`
- `facility_usage_011` -> `facility_usage`
- `tips_004` -> `tips`

현재 DB 기준 활성 문서 타입 목록:

| document_type | document_count |
| --- | ---: |
| admission | 32 |
| facility | 24 |
| facility_usage | 31 |
| intro | 9 |
| rules | 21 |
| tip | 8 |
| tips | 8 |

조회 API:

```http
GET /api/v1/regulations/document-types
GET /api/v1/regulations?document_type=facility
GET /api/v1/regulations?document_type=facility_usage
```

비고:
- `tip`과 `tips`는 현재 DB에 별도 타입으로 함께 존재합니다.
- 조회 API는 `is_active = true` 문서만 반환합니다.
