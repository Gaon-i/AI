# Gaon-i AI Server Development Guide

Gaon-i AI 서버의 초기 개발 환경과 개발 원칙을 정리한 문서입니다.

## Stack

- `FastAPI`
- `SQLAlchemy 2.x`
- `Alembic`
- `PostgreSQL`
- `pgvector`
- `Pydantic Settings`
- `pytest`

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
cp .env.example .env.dev
uvicorn app.main:app --reload
```

테스트 실행:

```bash
pytest
```

개발용 PostgreSQL 실행:

```bash
docker compose up -d
```

마이그레이션 적용:

```bash
alembic upgrade head
```

## Initial Structure

```text
Gaon-i/
  app/
    api/
    core/
    db/
      models/
    repositories/
    schemas/
    services/
  alembic/
  tests/
  .env.dev
  .env.prod
  pyproject.toml
  README.md
  DEV-README.md
```

## Environment Policy

- 모든 설정은 환경변수로 관리합니다.
- 개발 환경은 `.env.dev`를 사용합니다.
- 운영 환경은 `.env.prod` 또는 배포 환경의 시크릿/환경변수를 사용합니다.
- 애플리케이션은 `APP_ENV` 값을 기준으로 환경을 구분합니다.
- 민감한 값은 코드에 직접 넣지 않습니다.

예시:

```env
APP_ENV=dev
APP_NAME=gaon-i-ai
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/gaon_i
OPENAI_API_KEY=
```

## Database Policy

- 운영 대상 DB는 PostgreSQL입니다.
- 벡터 검색은 PostgreSQL의 `pgvector` 확장을 사용합니다.
- SQLAlchemy는 DB 연결, 모델 정의, 쿼리 처리를 담당합니다.
- Alembic은 스키마 버전 관리를 담당합니다.
- 스키마 변경은 직접 반영하지 않고 Alembic 마이그레이션으로 관리합니다.

## Testing Policy

이 프로젝트는 테스트 작성을 기본 원칙으로 합니다.

- 새로운 API를 추가하면 최소 1개 이상의 API 테스트를 작성합니다.
- 검색 또는 전처리 로직을 추가하면 단위 테스트를 작성합니다.
- DB 쿼리 또는 필터 조건이 추가되면 관련 테스트를 작성합니다.
- 버그를 수정하면 재발 방지 테스트를 함께 추가합니다.

초기 단계 최소 테스트:

- 헬스체크 API 테스트
- 설정 로딩 테스트
- DB 연결 테스트

## API Development Workflow

API 개발은 아래 순서를 기본 흐름으로 사용합니다.

1. FastAPI 엔드포인트를 작성합니다.
2. `/docs`에서 수동으로 호출해 요청과 응답을 확인합니다.
3. 동작이 확인되면 `pytest` 기반 API 테스트를 작성합니다.
4. 이후 수정 작업은 기존 테스트와 신규 테스트로 검증합니다.

`/docs`는 수동 확인과 빠른 점검을 위한 도구로 사용합니다. 자동 회귀 검증은 반드시 테스트 코드로 관리합니다.

## Setup Order

1. Python 가상환경 생성
2. FastAPI 프로젝트 뼈대 구성
3. 필수 패키지 설치
4. 환경변수 설정 구조 구성
5. FastAPI 실행 확인
6. SQLAlchemy DB 연결 구성
7. Alembic 초기화
8. PostgreSQL `pgvector` extension 확인
9. 첫 마이그레이션 생성 및 적용
10. 기본 테스트 작성 및 실행

## Team Rules

- 설정값은 하드코딩하지 않습니다.
- 스키마 변경은 수동 SQL 반영 대신 Alembic을 사용합니다.
- 기능 구현 전에 실행 환경과 테스트 기반을 먼저 맞춥니다.
- 검색 관련 핵심 로직은 재사용 가능한 함수 또는 서비스로 분리합니다.
- 코드가 추가되면 테스트도 함께 추가합니다.
