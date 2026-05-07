"""학생생활관 공지사항 목록/상세 페이지를 파싱하는 크롤러 서비스입니다."""

from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from typing import Optional
from urllib.parse import urlencode
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from app.schemas.notice import NoticeUpsertPayload

NOTICE_LIST_URL = "https://www.gachon.ac.kr/dormitory/2351/subview.do"
NOTICE_ARTICLE_LIMIT = 10
NOTICE_DATE_FORMAT = "%Y.%m.%d"
DETAIL_TEXT_BLOCK_TAGS = {
    "article",
    "dd",
    "div",
    "dt",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "li",
    "p",
    "td",
    "th",
}


@dataclass(frozen=True)
class NoticeListEntry:
    title: str
    source_url: str
    posted_at: datetime


def crawl_recent_notice_payloads(
    now: datetime,
    retention_days: int = 30,
    client: Optional[httpx.Client] = None,
    list_url: str = NOTICE_LIST_URL,
    article_limit: int = NOTICE_ARTICLE_LIMIT,
    max_pages: int = 10,
) -> list[NoticeUpsertPayload]:
    """최근 30일 공지의 목록과 상세 본문을 수집해 DB 적재용 payload로 반환합니다."""

    cutoff = now - timedelta(days=retention_days)
    close_client = client is None
    http_client = client or httpx.Client(
        timeout=10.0,
        headers={
            "User-Agent": "Gaon-i-NoticeCrawler/1.0",
        },
    )

    try:
        entries: list[NoticeListEntry] = []

        for page_index in range(max_pages):
            list_page_url = build_notice_list_page_url(
                list_url=list_url,
                article_offset=page_index * article_limit,
                article_limit=article_limit,
            )
            list_html = fetch_html(http_client, list_page_url)
            page_entries = parse_notice_list_page(list_html, base_url=list_url)
            if not page_entries:
                break

            recent_entries = [entry for entry in page_entries if entry.posted_at >= cutoff]
            entries.extend(recent_entries)

            if len(page_entries) < article_limit:
                break
            if any(entry.posted_at < cutoff for entry in page_entries):
                break

        payloads: list[NoticeUpsertPayload] = []
        for entry in entries:
            try:
                detail_html = fetch_html(http_client, entry.source_url)
                content = parse_notice_detail_page(detail_html, title=entry.title)
            except (httpx.HTTPError, ValueError):
                # 특정 공지 하나의 상세 파싱 실패가 전체 배치를 막지 않도록 건너뜁니다.
                continue
            payloads.append(
                NoticeUpsertPayload(
                    title=entry.title,
                    content=content,
                    source_url=entry.source_url,
                    posted_at=entry.posted_at,
                    collected_at=now,
                )
            )

        return payloads
    finally:
        if close_client:
            http_client.close()


def build_notice_list_page_url(
    list_url: str,
    article_offset: int,
    article_limit: int = NOTICE_ARTICLE_LIMIT,
) -> str:
    """학생생활관 게시판의 표준 페이징 쿼리 형태로 목록 URL을 만듭니다."""

    query = urlencode(
        {
            "mode": "list",
            "article.offset": article_offset,
            "articleLimit": article_limit,
        }
    )
    return f"{list_url}?{query}"


def fetch_html(client: httpx.Client, url: str) -> str:
    """외부 공지 페이지 HTML을 가져옵니다."""

    response = client.get(url, follow_redirects=True)
    response.raise_for_status()
    return response.text


def parse_notice_list_page(html: str, base_url: str = NOTICE_LIST_URL) -> list[NoticeListEntry]:
    """목록 HTML에서 공지 제목, 원문 링크, 등록일을 추출합니다."""

    soup = BeautifulSoup(html, "html.parser")
    entries: list[NoticeListEntry] = []
    seen_urls: set[str] = set()

    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        if "artclView.do" not in href:
            continue

        title = _normalize_text(anchor.get_text(" ", strip=True))
        if not title:
            continue

        container = anchor.find_parent(["tr", "li", "div"])
        container_text = _normalize_text(container.get_text(" ", strip=True)) if container else ""
        posted_at = _extract_posted_at(container_text)
        if posted_at is None:
            continue

        source_url = urljoin(base_url, href)
        if source_url in seen_urls:
            continue

        seen_urls.add(source_url)
        entries.append(
            NoticeListEntry(
                title=title,
                source_url=source_url,
                posted_at=posted_at,
            )
        )

    return entries


def parse_notice_detail_page(html: str, title: str) -> str:
    """상세 HTML에서 본문 텍스트만 추출합니다."""

    soup = BeautifulSoup(html, "html.parser")
    text_lines = _extract_detail_text_lines(soup)
    if not text_lines:
        raise ValueError("failed to extract notice detail content")

    content_start_index = _find_content_start_index(text_lines)
    content_end_index = _find_content_end_index(text_lines)
    content_lines = text_lines[content_start_index:content_end_index]

    normalized_title = _normalize_text(title)
    while content_lines and content_lines[0] == normalized_title:
        content_lines = content_lines[1:]

    content = "\n".join(content_lines).strip()
    if not content:
        raise ValueError("failed to extract notice detail content")
    return content


def _extract_detail_text_lines(soup: BeautifulSoup) -> list[str]:
    """블록 경계는 보존하고, 블록 내부의 조각난 inline 텍스트는 한 줄로 합칩니다."""

    text_lines: list[str] = []

    for element in soup.find_all(DETAIL_TEXT_BLOCK_TAGS):
        if element.find(DETAIL_TEXT_BLOCK_TAGS):
            continue

        text = _normalize_text(element.get_text(" ", strip=True))
        if not text:
            continue

        text_lines.append(text)

    if text_lines:
        return text_lines

    return [
        _normalize_text(line)
        for line in soup.get_text("\n", strip=True).splitlines()
        if _normalize_text(line)
    ]


def _extract_posted_at(text: str) -> Optional[datetime]:
    for token in text.split():
        if len(token) == 10 and token[4] == "." and token[7] == ".":
            try:
                return datetime.strptime(token, NOTICE_DATE_FORMAT)
            except ValueError:
                continue
    return None


def _find_content_start_index(lines: list[str]) -> int:
    for index, line in enumerate(lines):
        if line == "등록일" and index + 2 < len(lines):
            return index + 2
    for index, line in enumerate(lines):
        if _extract_posted_at(line) is not None:
            return index + 1
    return 0


def _find_content_end_index(lines: list[str]) -> int:
    for index, line in enumerate(lines):
        if line == "첨부파일":
            return index
    return len(lines)


def _normalize_text(value: str) -> str:
    return " ".join(value.split())
