"""호실 번호 기반 층수 질문을 규칙 기반으로 처리하는 서비스입니다."""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class RoomFloorResult:
    answer: str
    source_url: str = ""


ROOM_FLOOR_RANGES: dict[str, list[tuple[int, int, int]]] = {
    "제1학생생활관": [
        (101, 117, 1),
        (201, 217, 2),
        (301, 317, 3),
        (401, 417, 4),
        (501, 504, 5),
        (121, 144, 1),
        (221, 244, 2),
        (321, 344, 3),
        (421, 444, 4),
        (521, 536, 5),
    ],
    "제2학생생활관": [
        (101, 141, 1),
        (201, 246, 2),
        (301, 346, 3),
        (401, 446, 4),
        (501, 546, 5),
        (151, 170, 1),
        (251, 276, 2),
        (351, 384, 3),
        (451, 484, 4),
        (551, 584, 5),
    ],
    "제3학생생활관": [
        (201, 236, 2),
        (301, 336, 3),
        (401, 436, 4),
        (501, 536, 5),
        (251, 275, 2),
        (351, 375, 3),
        (451, 475, 4),
        (551, 575, 5),
    ],
}


def resolve_room_floor_question(
    question: str,
    dormitory: Optional[str],
) -> Optional[RoomFloorResult]:
    """
    '401호 몇 층이야?'처럼 호실 번호로 층수를 묻는 질문이면 규칙 기반으로 답변한다.
    해당 질문이 아니면 None을 반환한다.
    """

    if not dormitory:
        return None

    if not _looks_like_room_floor_question(question):
        return None

    room_number = _extract_room_number(question)
    if room_number is None:
        return None

    ranges = ROOM_FLOOR_RANGES.get(dormitory)
    if not ranges:
        return RoomFloorResult(
            answer=f"{dormitory}의 호실 층수 정보를 확인할 수 없습니다."
        )


    for start, end, floor in ranges:
        if start <= room_number <= end:
            return RoomFloorResult(
                answer=f"{room_number}호는 {dormitory} 지상 {floor}층에 위치합니다."
            )

    return RoomFloorResult(
        answer=f"{dormitory}에서 {room_number}호에 대한 층수 정보는 확인되지 않습니다."
    )


def _looks_like_room_floor_question(question: str) -> bool:
    compact_question = question.replace(" ", "")

    has_room_number = re.search(r"\d{3,4}호", compact_question) is not None
    asks_floor = any(
        keyword in compact_question
        for keyword in ["몇층", "몇층이야", "층이야", "층인가", "어디층"]
    )

    return has_room_number and asks_floor


def _extract_room_number(question: str) -> Optional[int]:
    compact_question = question.replace(" ", "")
    match = re.search(r"(?<!\d)(\d{3,4})호", compact_question)
    if not match:
        return None

    return int(match.group(1))
