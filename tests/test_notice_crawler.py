"""notice crawler가 목록/상세 HTML을 기대한 형태로 파싱하는지 검증합니다."""

from datetime import datetime

from app.services.notice_crawler import build_notice_list_page_url
from app.services.notice_crawler import crawl_recent_notice_payloads
from app.services.notice_crawler import parse_notice_detail_page
from app.services.notice_crawler import parse_notice_list_page


LIST_HTML = """
<html>
  <body>
    <table>
      <tbody>
        <tr>
          <td>200</td>
          <td><a href="/bbs/dormitory/330/118553/artclView.do">2026년 상반기 화재대피훈련 온라인 교육 참여 및 참여보고서 제출 안내</a></td>
          <td>학생생활관</td>
          <td>2026.03.19</td>
        </tr>
        <tr>
          <td>199</td>
          <td><a href="/bbs/dormitory/330/118554/artclView.do">2026-1학기 학생생활관 1차 생활점검 안내</a></td>
          <td>학생생활관</td>
          <td>2026.03.18</td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""

DETAIL_HTML = """
<html>
  <body>
    <div>글번호</div>
    <div>118553</div>
    <h2>2026년 상반기 화재대피훈련 온라인 교육 참여 및 참여보고서 제출 안내</h2>
    <div>수정일</div>
    <div>2026.03.19</div>
    <div>작성자</div>
    <div>학생생활관</div>
    <div>조회수</div>
    <div>190</div>
    <div>등록일</div>
    <div>2026.03.19</div>
    <div>2026년 상반기 화재대피훈련 온라인 교육 참여 및 참여보고서 제출 안내</div>
    <div>‘26 년 상반기 화재대피훈련을 온라인 교육으로 실시합니다.</div>
    <div>1. 온라인 교육 실시일 : 2026 년 3 월 25 일(수) ~ 3 월 31 일(화) 20 시까지</div>
    <div>2. 참여보고서 제출 : 해당 생활관 사감실 제출</div>
    <div>첨부파일</div>
    <div>file.pdf</div>
  </body>
</html>
"""


class FakeResponse:
    def __init__(self, text: str, status_code: int = 200) -> None:
        self.text = text
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError("http error")


class FakeClient:
    def __init__(self, responses: dict[str, str]) -> None:
        self.responses = responses
        self.requested_urls: list[str] = []

    def get(self, url: str, follow_redirects: bool = False) -> FakeResponse:
        self.requested_urls.append(url)
        if url not in self.responses:
            raise AssertionError(f"unexpected url requested: {url}")
        return FakeResponse(self.responses[url])


def test_build_notice_list_page_url_uses_expected_pagination_query() -> None:
    url = build_notice_list_page_url(
        list_url="https://www.gachon.ac.kr/dormitory/2351/subview.do",
        article_offset=20,
        article_limit=10,
    )

    assert url == (
        "https://www.gachon.ac.kr/dormitory/2351/subview.do"
        "?mode=list&article.offset=20&articleLimit=10"
    )


def test_parse_notice_list_page_extracts_title_url_and_posted_at() -> None:
    entries = parse_notice_list_page(LIST_HTML)

    assert len(entries) == 2
    assert entries[0].title == "2026년 상반기 화재대피훈련 온라인 교육 참여 및 참여보고서 제출 안내"
    assert entries[0].source_url == "https://www.gachon.ac.kr/bbs/dormitory/330/118553/artclView.do"
    assert entries[0].posted_at == datetime(2026, 3, 19, 0, 0, 0)


def test_parse_notice_detail_page_extracts_body_without_metadata_and_attachments() -> None:
    content = parse_notice_detail_page(
        DETAIL_HTML,
        title="2026년 상반기 화재대피훈련 온라인 교육 참여 및 참여보고서 제출 안내",
    )

    assert "등록일" not in content
    assert "첨부파일" not in content
    assert "‘26 년 상반기 화재대피훈련을 온라인 교육으로 실시합니다." in content
    assert "2. 참여보고서 제출 : 해당 생활관 사감실 제출" in content


def test_crawl_recent_notice_payloads_filters_old_notices_and_fetches_details() -> None:
    page_1_url = (
        "https://www.gachon.ac.kr/dormitory/2351/subview.do"
        "?mode=list&article.offset=0&articleLimit=2"
    )
    page_2_url = (
        "https://www.gachon.ac.kr/dormitory/2351/subview.do"
        "?mode=list&article.offset=2&articleLimit=2"
    )
    page_1_html = """
    <table><tbody>
      <tr><td><a href="/bbs/dormitory/330/1/artclView.do">최근 공지 1</a></td><td>2026.04.10</td></tr>
      <tr><td><a href="/bbs/dormitory/330/2/artclView.do">최근 공지 2</a></td><td>2026.04.02</td></tr>
    </tbody></table>
    """
    page_2_html = """
    <table><tbody>
      <tr><td><a href="/bbs/dormitory/330/3/artclView.do">최근 공지 3</a></td><td>2026.03.20</td></tr>
      <tr><td><a href="/bbs/dormitory/330/4/artclView.do">오래된 공지</a></td><td>2026.03.01</td></tr>
    </tbody></table>
    """
    detail_html = """
    <div>등록일</div><div>2026.04.10</div><div>{title}</div><div>{body}</div><div>첨부파일</div>
    """
    client = FakeClient(
        {
            page_1_url: page_1_html,
            page_2_url: page_2_html,
            "https://www.gachon.ac.kr/bbs/dormitory/330/1/artclView.do": detail_html.format(
                title="최근 공지 1",
                body="최근 공지 1 본문",
            ),
            "https://www.gachon.ac.kr/bbs/dormitory/330/2/artclView.do": detail_html.format(
                title="최근 공지 2",
                body="최근 공지 2 본문",
            ),
            "https://www.gachon.ac.kr/bbs/dormitory/330/3/artclView.do": detail_html.format(
                title="최근 공지 3",
                body="최근 공지 3 본문",
            ),
        }
    )

    payloads = crawl_recent_notice_payloads(
        now=datetime(2026, 4, 12, 12, 0, 0),
        retention_days=30,
        client=client,
        article_limit=2,
        max_pages=3,
    )

    assert [payload.title for payload in payloads] == ["최근 공지 1", "최근 공지 2", "최근 공지 3"]
    assert [payload.content for payload in payloads] == [
        "최근 공지 1 본문",
        "최근 공지 2 본문",
        "최근 공지 3 본문",
    ]
    assert all(payload.collected_at == datetime(2026, 4, 12, 12, 0, 0) for payload in payloads)
    assert "https://www.gachon.ac.kr/bbs/dormitory/330/4/artclView.do" not in client.requested_urls
