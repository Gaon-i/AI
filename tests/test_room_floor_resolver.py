from app.services.room_floor_resolver import RoomFloorResult
from app.services.room_floor_resolver import resolve_room_floor_question


def test_resolve_room_floor_question_returns_floor_for_known_room() -> None:
    result = resolve_room_floor_question("401호 몇 층이야?", "제1학생생활관")

    assert result == RoomFloorResult(
        answer="401호는 제1학생생활관 지상 4층에 위치합니다."
    )


def test_resolve_room_floor_question_accepts_spaced_floor_question() -> None:
    result = resolve_room_floor_question("251호는 어디 층인가요?", "제2학생생활관")

    assert result == RoomFloorResult(
        answer="251호는 제2학생생활관 지상 2층에 위치합니다."
    )


def test_resolve_room_floor_question_ignores_non_floor_question() -> None:
    result = resolve_room_floor_question("401호에 택배 받을 수 있어?", "제1학생생활관")

    assert result is None


def test_resolve_room_floor_question_requires_dormitory() -> None:
    result = resolve_room_floor_question("401호 몇 층이야?", None)

    assert result is None


def test_resolve_room_floor_question_returns_message_for_unknown_dormitory() -> None:
    result = resolve_room_floor_question("401호 몇 층이야?", "행복기숙사")

    assert result == RoomFloorResult(
        answer="행복기숙사의 호실 층수 정보를 확인할 수 없습니다."
    )


def test_resolve_room_floor_question_returns_message_for_unknown_room() -> None:
    result = resolve_room_floor_question("999호 몇 층이야?", "제1학생생활관")

    assert result == RoomFloorResult(
        answer="제1학생생활관에서 999호에 대한 층수 정보는 확인되지 않습니다."
    )
