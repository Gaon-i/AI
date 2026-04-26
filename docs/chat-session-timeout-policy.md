# Chat Session Timeout Policy

## 개요

채팅 세션은 `chat_session` 테이블에 저장되며, 각 질문은 `chat_log`로 기록됩니다.  
현재 정책은 별도의 "대화 종료" 버튼 없이 `last_activity_at` 기준 비활성 시간을 계산해 세션 유효 여부를 판단합니다.

기본 설정값:

- `chat_session_timeout_minutes = 30`

즉, 마지막 질문 처리 시각으로부터 30분 이상 추가 질문이 없으면 해당 세션은 만료된 것으로 간주합니다.

## 정책 상세

### 1. 세션 생성

- `POST /api/v1/ai/chat/sessions`
- 응답으로 `session_id`를 발급합니다.

### 2. 세션 사용

- `POST /api/v1/ai/chat`
- 요청 바디에 `session_id`를 반드시 포함해야 합니다.
- 서버는 `chat_session`을 조회한 뒤, 아래 순서로 검사합니다.

검사 순서:

1. `session_id`가 실제로 존재하는가
2. `last_activity_at`이 현재 시각 기준 30분 이내인가
3. 유효하면 `chat_log`를 `PROCESSING` 상태로 생성하고 답변 처리를 시작

### 3. 세션 만료

만료 조건:

- `datetime.utcnow() - last_activity_at > 30분`

만료된 세션에 대해서는:

- 새 `chat_log`를 만들지 않습니다.
- `chat_session.total_turns`를 증가시키지 않습니다.
- `chat_session.last_activity_at`를 갱신하지 않습니다.
- 클라이언트에 만료 에러를 반환합니다.

### 4. 재시작 방식

현재는 명시 종료 API가 없으므로, 만료된 세션은 재사용하지 않습니다.

클라이언트 처리 권장 흐름:

1. `/api/v1/ai/chat` 호출
2. `CHAT_SESSION_EXPIRED` 응답 수신
3. `/api/v1/ai/chat/sessions`로 새 세션 발급
4. 새 `session_id`로 질문 재전송

## 에러 코드

### `CHAT_SESSION_NOT_FOUND`

- HTTP Status: `404`
- 의미: 요청에 포함된 `session_id`가 DB에 존재하지 않음
- 예시 상황:
  - 잘못된 세션 ID 전달
  - 이미 다른 환경에서 사용하던 임의 값 전달

예시 응답:

```json
{
  "status": 404,
  "message": "chat session not found",
  "data": null,
  "error_code": "CHAT_SESSION_NOT_FOUND"
}
```

### `CHAT_SESSION_EXPIRED`

- HTTP Status: `409`
- 의미: 세션은 존재하지만 비활성 30분을 초과해 더 이상 사용할 수 없음
- 예시 상황:
  - 앱을 오래 켜두고 다시 질문한 경우
  - 이전 대화를 복구하려다 만료된 `session_id`를 재사용한 경우

예시 응답:

```json
{
  "status": 409,
  "message": "chat session expired after 30 minutes of inactivity. please start a new chat session",
  "data": null,
  "error_code": "CHAT_SESSION_EXPIRED"
}
```

## 구현 메모

- 설정 위치: [config.py](/Users/kimssirr/Documents/Playground/Gaon-i/app/core/config.py)
- 만료 판단 위치: [chat_service.py](/Users/kimssirr/Documents/Playground/Gaon-i/app/services/chat_service.py)
- 공통 에러 코드 위치: [error_codes.py](/Users/kimssirr/Documents/Playground/Gaon-i/app/core/error_codes.py)

## 수동 테스트 시나리오

### 정상 흐름

1. `POST /api/v1/ai/chat/sessions` 호출
2. 받은 `session_id`로 즉시 `POST /api/v1/ai/chat` 호출
3. `SUCCESS` 또는 `NO_ANSWER` 응답 확인

### 존재하지 않는 세션

1. 임의의 `session_id`로 `POST /api/v1/ai/chat` 호출
2. `404`, `CHAT_SESSION_NOT_FOUND` 응답 확인

### 만료된 세션

1. 세션 생성 후 `last_activity_at`를 강제로 30분 이전으로 조정
2. 해당 `session_id`로 `POST /api/v1/ai/chat` 호출
3. `409`, `CHAT_SESSION_EXPIRED` 응답 확인
