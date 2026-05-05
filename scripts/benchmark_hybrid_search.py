"""Benchmark hybrid regulation chunk search before/after DB indexing changes.

This script intentionally avoids calling external embedding or LLM APIs. It uses
a stable synthetic query embedding with the same dimension as stored chunk
embeddings, then runs the repository search functions directly so DB search cost
can be compared with less application-level noise.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.repositories import regulation_chunk_repository as repo


DEFAULT_CASES = [
    {
        "name": "single_curfew_keyword",
        "function": "single",
        "query_text": "통금",
        "dormitory": "제1학생생활관",
        "top_k": 3,
        "candidate_k": 20,
    },
    {
        "name": "single_curfew_when",
        "function": "single",
        "query_text": "통금시간 언제까지야??",
        "dormitory": "제2학생생활관",
        "top_k": 3,
        "candidate_k": 20,
    },
    {
        "name": "single_ramen_cook",
        "function": "single",
        "query_text": "방에서 라면 끓여먹어도 돼?",
        "dormitory": "제1학생생활관",
        "top_k": 3,
        "candidate_k": 20,
    },
    {
        "name": "single_ramen_eat",
        "function": "single",
        "query_text": "방에서 라면 먹어도 돼?",
        "dormitory": "제2학생생활관",
        "top_k": 3,
        "candidate_k": 20,
    },
    {
        "name": "single_convenience_store",
        "function": "single",
        "query_text": "2긱에 편의점 있어?",
        "dormitory": "제2학생생활관",
        "top_k": 3,
        "candidate_k": 20,
    },
    {
        "name": "single_atm",
        "function": "single",
        "query_text": "2긱에 atm기 있어?",
        "dormitory": "제2학생생활관",
        "top_k": 3,
        "candidate_k": 20,
    },
    {
        "name": "single_no_match",
        "function": "single",
        "query_text": "화성 탐사선 주차 규정",
        "dormitory": "제1학생생활관",
        "top_k": 3,
        "candidate_k": 20,
    },
    {
        "name": "all_curfew_keyword",
        "function": "all",
        "query_text": "통금",
        "top_k": 5,
        "candidate_k": 30,
    },
    {
        "name": "all_capacity",
        "function": "all",
        "query_text": "기숙사 수용인원 몇명이야?",
        "top_k": 5,
        "candidate_k": 30,
    },
    {
        "name": "all_convenience_store",
        "function": "all",
        "query_text": "편의점 어디있어?",
        "top_k": 5,
        "candidate_k": 30,
    },
    {
        "name": "all_cost",
        "function": "all",
        "query_text": "기숙사 비용 얼마야?",
        "top_k": 5,
        "candidate_k": 30,
    },
    {
        "name": "grouped_cooking_keyword",
        "function": "grouped",
        "query_text": "취사",
        "top_k": 3,
        "candidate_k": 20,
    },
    {
        "name": "grouped_ramen_cook",
        "function": "grouped",
        "query_text": "라면 끓여 먹어도 돼?",
        "top_k": 3,
        "candidate_k": 20,
    },
    {
        "name": "grouped_ramen_eat_typo",
        "function": "grouped",
        "query_text": "방에서 라면 먹어도돼??",
        "top_k": 3,
        "candidate_k": 20,
    },
    {
        "name": "grouped_printer",
        "function": "grouped",
        "query_text": "프린트할 곳 있어?",
        "top_k": 3,
        "candidate_k": 20,
    },
    {
        "name": "grouped_cash_machine",
        "function": "grouped",
        "query_text": "현금자동입출기 있어?",
        "top_k": 3,
        "candidate_k": 20,
    },
    {
        "name": "grouped_no_match",
        "function": "grouped",
        "query_text": "화성 탐사선 주차 규정",
        "top_k": 3,
        "candidate_k": 20,
    },
]


@dataclass(frozen=True)
class CapturedQuery:
    sql: str
    params: dict[str, Any]


class _EmptyMappingResult:
    def mappings(self) -> "_EmptyMappingResult":
        return self

    def all(self) -> list[Any]:
        return []


class _CaptureSession:
    def __init__(self) -> None:
        self.captured: CapturedQuery | None = None

    def execute(self, statement: Any, params: dict[str, Any] | None = None) -> _EmptyMappingResult:
        self.captured = CapturedQuery(sql=str(statement), params=params or {})
        return _EmptyMappingResult()


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark hybrid search repository functions.")
    parser.add_argument("--iterations", type=int, default=50)
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--keyword-weight", type=float, default=0.3)
    parser.add_argument(
        "--embedding-mode",
        choices=["anchor", "zero"],
        default="anchor",
        help="Use an existing chunk embedding as a stable anchor, or a zero vector.",
    )
    parser.add_argument(
        "--sample-keyword-cases",
        type=int,
        default=3,
        help="Append this many DB-derived keyword cases with known active chunks.",
    )
    parser.add_argument("--explain", action="store_true", help="Also collect EXPLAIN ANALYZE BUFFERS JSON.")
    parser.add_argument(
        "--include-raw-plan",
        action="store_true",
        help="Include full EXPLAIN FORMAT JSON plans. By default only plan summaries are emitted.",
    )
    parser.add_argument("--output", type=Path, help="Write benchmark result JSON to this path.")
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL"),
        help="Override settings.database_url, useful for local before/after benchmarking.",
    )
    args = parser.parse_args()

    settings = get_settings()
    database_url = args.database_url or settings.database_url
    session_factory = sessionmaker(
        bind=create_engine(database_url, future=True),
        autocommit=False,
        autoflush=False,
        class_=Session,
    )
    db = session_factory()

    try:
        embedding_dimension = _get_embedding_dimension(db, settings.openai_embedding_dimension)
        query_embedding = _get_query_embedding(db, args.embedding_mode, embedding_dimension)
        cases = DEFAULT_CASES + _get_sample_keyword_cases(db, args.sample_keyword_cases)

        result = {
            "metadata": {
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "app_env": settings.app_env,
                "database_url": _redact_database_url(database_url),
                "iterations": args.iterations,
                "warmup": args.warmup,
                "keyword_weight": args.keyword_weight,
                "embedding_mode": args.embedding_mode,
                "embedding_dimension": embedding_dimension,
                "case_count": len(cases),
                "active_chunk_count": _scalar_int(
                    db,
                    """
                    SELECT COUNT(*)
                    FROM regulation_chunk rc
                    JOIN regulation_document rd
                      ON rd.regulation_document_id = rc.regulation_document_id
                    WHERE rc.is_active = TRUE
                      AND rd.is_active = TRUE
                      AND rc.embedding IS NOT NULL
                    """,
                ),
            },
            "cases": [],
        }

        for case in cases:
            benchmark = _benchmark_case(
                db=db,
                case=case,
                query_embedding=query_embedding,
                iterations=args.iterations,
                warmup=args.warmup,
                keyword_weight=args.keyword_weight,
                grouped_dormitories=settings.chat_grouped_dormitories,
            )

            if args.explain:
                benchmark["explain"] = _explain_case(
                    db=db,
                    case=case,
                    query_embedding=query_embedding,
                    keyword_weight=args.keyword_weight,
                    grouped_dormitories=settings.chat_grouped_dormitories,
                    include_raw_plan=args.include_raw_plan,
                )

            result["cases"].append(benchmark)

        payload = json.dumps(result, ensure_ascii=False, indent=2)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(payload + "\n", encoding="utf-8")

        print(payload)
    finally:
        db.close()


def _benchmark_case(
    *,
    db: Any,
    case: dict[str, Any],
    query_embedding: list[float],
    iterations: int,
    warmup: int,
    keyword_weight: float,
    grouped_dormitories: list[str],
) -> dict[str, Any]:
    for _ in range(warmup):
        _run_case(
            db=db,
            case=case,
            query_embedding=query_embedding,
            keyword_weight=keyword_weight,
            grouped_dormitories=grouped_dormitories,
        )

    elapsed_ms = []
    last_rows = []
    for _ in range(iterations):
        started_at = time.perf_counter()
        last_rows = _run_case(
            db=db,
            case=case,
            query_embedding=query_embedding,
            keyword_weight=keyword_weight,
            grouped_dormitories=grouped_dormitories,
        )
        elapsed_ms.append((time.perf_counter() - started_at) * 1000)

    return {
        "name": case["name"],
        "function": case["function"],
        "query_text": case["query_text"],
        "top_k": case["top_k"],
        "candidate_k": case["candidate_k"],
        "timing_ms": _summarize_timings(elapsed_ms),
        "top_results": [
            {
                "regulation_chunk_id": row["regulation_chunk_id"],
                "document_id": row["document_id"],
                "retrieval_group": row["retrieval_group"],
                "hybrid_score": row.get("hybrid_score"),
                "vector_score": row.get("vector_score"),
                "keyword_score": row.get("keyword_score"),
            }
            for row in last_rows
        ],
    }


def _run_case(
    *,
    db: Any,
    case: dict[str, Any],
    query_embedding: list[float],
    keyword_weight: float,
    grouped_dormitories: list[str],
) -> list[dict[str, Any]]:
    common = {
        "query_text": case["query_text"],
        "query_embedding": query_embedding,
        "top_k": case["top_k"],
        "candidate_k": case["candidate_k"],
        "keyword_weight": keyword_weight,
    }

    if case["function"] == "single":
        return repo.search_hybrid_chunks(db=db, dormitory=case["dormitory"], **common)
    if case["function"] == "all":
        return repo.search_hybrid_chunks_all_dormitories(db=db, **common)
    if case["function"] == "grouped":
        return repo.search_hybrid_chunks_for_dormitories(
            db=db,
            dormitories=grouped_dormitories,
            **common,
        )

    raise ValueError(f"Unknown benchmark function: {case['function']}")


def _explain_case(
    *,
    db: Any,
    case: dict[str, Any],
    query_embedding: list[float],
    keyword_weight: float,
    grouped_dormitories: list[str],
    include_raw_plan: bool,
) -> dict[str, Any]:
    capture_db = _CaptureSession()
    _run_case(
        db=capture_db,
        case=case,
        query_embedding=query_embedding,
        keyword_weight=keyword_weight,
        grouped_dormitories=grouped_dormitories,
    )

    if capture_db.captured is None:
        raise RuntimeError(f"Failed to capture SQL for benchmark case {case['name']}")

    explain_sql = text("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + capture_db.captured.sql)
    explain_result = db.execute(explain_sql, capture_db.captured.params).scalar_one()
    plan = explain_result[0]

    explain = {
        "planning_time_ms": plan.get("Planning Time"),
        "execution_time_ms": plan.get("Execution Time"),
        "top_plan_node": plan.get("Plan", {}).get("Node Type"),
        "plan_summary": _summarize_plan(plan.get("Plan", {})),
    }
    if include_raw_plan:
        explain["raw_plan"] = plan

    return explain


def _summarize_timings(values: list[float]) -> dict[str, float]:
    sorted_values = sorted(values)
    return {
        "min": round(sorted_values[0], 3),
        "avg": round(statistics.fmean(sorted_values), 3),
        "median": round(statistics.median(sorted_values), 3),
        "p95": round(_percentile(sorted_values, 95), 3),
        "max": round(sorted_values[-1], 3),
    }


def _percentile(sorted_values: list[float], percentile: float) -> float:
    if len(sorted_values) == 1:
        return sorted_values[0]

    rank = (len(sorted_values) - 1) * (percentile / 100)
    lower = int(rank)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = rank - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def _summarize_plan(plan: dict[str, Any]) -> dict[str, Any]:
    node_counts: dict[str, int] = {}
    index_names: set[str] = set()

    def visit(node: dict[str, Any]) -> None:
        node_type = node.get("Node Type")
        if node_type:
            node_counts[node_type] = node_counts.get(node_type, 0) + 1
        index_name = node.get("Index Name")
        if index_name:
            index_names.add(index_name)
        for child in node.get("Plans", []):
            visit(child)

    visit(plan)
    return {
        "node_counts": dict(sorted(node_counts.items())),
        "index_names": sorted(index_names),
        "shared_hit_blocks": _sum_plan_value(plan, "Shared Hit Blocks"),
        "shared_read_blocks": _sum_plan_value(plan, "Shared Read Blocks"),
        "temp_read_blocks": _sum_plan_value(plan, "Temp Read Blocks"),
        "temp_written_blocks": _sum_plan_value(plan, "Temp Written Blocks"),
    }


def _sum_plan_value(plan: dict[str, Any], key: str) -> int:
    total = int(plan.get(key, 0) or 0)
    for child in plan.get("Plans", []):
        total += _sum_plan_value(child, key)
    return total


def _get_embedding_dimension(db: Any, fallback: int) -> int:
    dimension = db.execute(
        text(
            """
            SELECT vector_dims(embedding)
            FROM regulation_chunk
            WHERE embedding IS NOT NULL
            LIMIT 1
            """
        )
    ).scalar_one_or_none()
    return int(dimension or fallback)


def _get_query_embedding(db: Any, embedding_mode: str, embedding_dimension: int) -> list[float]:
    if embedding_mode == "zero":
        return [0.0] * embedding_dimension

    embedding = db.execute(
        text(
            """
            SELECT embedding::text
            FROM regulation_chunk
            WHERE is_active = TRUE
              AND embedding IS NOT NULL
            ORDER BY regulation_chunk_id
            LIMIT 1
            """
        )
    ).scalar_one_or_none()
    if embedding is None:
        return [0.0] * embedding_dimension

    return [float(value) for value in embedding.strip("[]").split(",")]


def _get_sample_keyword_cases(db: Any, limit: int) -> list[dict[str, Any]]:
    if limit <= 0:
        return []

    rows = db.execute(
        text(
            """
            SELECT
                rc.regulation_chunk_id,
                rd.dormitory,
                keyword
            FROM regulation_chunk rc
            JOIN regulation_document rd
              ON rd.regulation_document_id = rc.regulation_document_id
            CROSS JOIN LATERAL jsonb_array_elements_text(rc.keywords) AS keyword
            WHERE rc.is_active = TRUE
              AND rd.is_active = TRUE
              AND rc.embedding IS NOT NULL
              AND rc.keywords IS NOT NULL
              AND jsonb_array_length(rc.keywords) > 0
            ORDER BY rc.regulation_chunk_id
            LIMIT :limit
            """
        ),
        {"limit": limit},
    ).mappings().all()

    cases = []
    for index, row in enumerate(rows, start=1):
        keyword = str(row.keyword).strip()
        if not keyword:
            continue

        if row.dormitory:
            cases.append(
                {
                    "name": f"sample_keyword_single_{index}",
                    "function": "single",
                    "query_text": keyword,
                    "dormitory": row.dormitory,
                    "top_k": 3,
                    "candidate_k": 20,
                    "sample_regulation_chunk_id": row.regulation_chunk_id,
                }
            )
        else:
            cases.append(
                {
                    "name": f"sample_keyword_all_{index}",
                    "function": "all",
                    "query_text": keyword,
                    "top_k": 5,
                    "candidate_k": 30,
                    "sample_regulation_chunk_id": row.regulation_chunk_id,
                }
            )

    return cases


def _scalar_int(db: Any, sql: str) -> int:
    return int(db.execute(text(sql)).scalar_one())


def _redact_database_url(database_url: str) -> str:
    if "@" not in database_url or "://" not in database_url:
        return database_url

    scheme, rest = database_url.split("://", 1)
    return f"{scheme}://***@{rest.split('@', 1)[1]}"


if __name__ == "__main__":
    main()
