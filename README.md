# Gaon-i AI

Gaon-i AI 저장소입니다.

이 저장소는 `main`, `dev`, 기능 브랜치 기반으로 협업하며, 개발 환경과 구현 상세는 [DEV-README.md](/Users/kimssirr/Documents/Playground/Gaon-i/DEV-README.md)에서 관리합니다.

## Documents

- 개발 환경 가이드: [DEV-README.md](/Users/kimssirr/Documents/Playground/Gaon-i/DEV-README.md)
- Pull Request 템플릿: `.github/pull_request_template.md`
- Issue 템플릿: `.github/ISSUE_TEMPLATE/`

## Collaboration Rules

### 1. Branch Strategy

본 프로젝트는 GitHub Flow 기반으로 브랜치를 운영합니다.

#### Branch Types

- `main`
  - 제품 출시 브랜치이며 최종 배포 대상 브랜치입니다.
- `dev`
  - 통합 개발 브랜치입니다.
  - 기능 브랜치에서 개발한 내용을 병합하여 테스트와 검증을 진행합니다.
- `feat/#issue-number`
  - 새로운 기능 개발 브랜치입니다.
- `fix/#issue-number`
  - 버그 수정 브랜치입니다.

#### Branch Naming

```bash
feat/#12
fix/#23
```

#### Branch Workflow

1. 이슈를 생성합니다.
2. 이슈 번호에 맞는 브랜치를 생성합니다.
3. 기능 개발 또는 버그 수정을 진행합니다.
4. 작업 완료 후 Pull Request를 생성합니다.
5. 리뷰와 CI 검사를 통과하면 `dev` 브랜치에 병합합니다.
6. 충분한 테스트와 검증이 완료되면 `main` 브랜치에 병합하고 배포합니다.

### 2. Pull Request Rules

#### PR Title Format

```text
feat: 로그인 API 구현
fix: 회원가입 시 닉네임 중복 오류 수정
docs: README 실행 방법 수정
```

#### PR Writing Rules

Pull Request는 반드시 템플릿 기반으로 작성합니다.

다음 항목을 포함합니다.

- 유형
- 작업 내용
- 변경 사항
- 리뷰 포인트
- 관련 이슈

#### PR Tags

| Tag | Description |
| --- | --- |
| `[Feat]` | 새로운 기능 추가 |
| `[Fix]` | 버그 수정 |
| `[Design]` | API 응답 포맷, UI 관련 수정 |
| `[Docs]` | 문서 수정 |
| `[Chore]` | 설정 변경, 의존성 관리, 빌드 관련 작업 |
| `[Hotfix]` | 배포 중 긴급 수정 |

#### PR Examples

```text
[Feat] 로그인 API 구현
[Fix] 회원가입 시 닉네임 중복 오류 수정
[Docs] README 실행 방법 수정
```

### 3. Commit Convention

#### Commit Message Format

```text
<tag>: <title>

- 작업 내용 상세
- 작업 내용 상세2

#이슈번호 (optional)
```

#### Commit Tags

| Tag | Description |
| --- | --- |
| `feat` | 새로운 기능 추가 |
| `fix` | 버그 수정 |
| `design` | API 응답 포맷, UI 관련 수정 |
| `docs` | 문서 수정 |
| `chore` | 설정 변경, 의존성 관리, 빌드 관련 작업 |
| `hotfix` | 긴급 수정 |

#### Commit Examples

```text
feat: 회원가입 API 구현

- 회원가입 요청 DTO 및 엔티티 생성
- 회원가입 서비스 로직 구현
- 비밀번호 암호화 처리 적용

#12
```

```text
fix: 회원가입 시 닉네임 중복 오류 수정

- 닉네임 중복 검사 로직 수정
- 예외 처리 메시지 통일

#23
```

### 4. Collaboration Process

```text
1. 이슈 생성
2. 브랜치 생성 (feat/#issue-number 또는 fix/#issue-number)
3. 기능 개발 및 커밋
4. Pull Request 생성
5. 코드 리뷰 및 CI 검사 진행
6. dev 브랜치 병합
7. 테스트 완료 후 main 브랜치 병합 및 배포
```
