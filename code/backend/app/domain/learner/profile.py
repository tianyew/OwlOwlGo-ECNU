"""Replayable evidence summaries; repeated questions do not create new coverage."""

from datetime import UTC, datetime

DIMENSIONS = {
    "phonetics": "拼音与声调",
    "vocabulary": "词汇与句式",
    "reading": "功能性阅读",
    "information": "非连续性文本信息处理",
    "poetry": "古诗理解",
    "classical": "文言文理解",
    "writing": "书面表达与修改",
}
BLOOM = {
    "remember": "记忆",
    "understand": "理解",
    "apply": "应用",
    "analyze": "分析",
    "evaluate": "评价",
    "create": "创造",
}
PROFILE_VERSION = "first-evidence-v1"


def statistics(items: list[dict]) -> dict:
    unique = {}
    latest = {}
    for item in items:
        source = item["source_question_id"]
        unique.setdefault(source, item)
        latest[source] = item
    count = len(unique)
    correct = sum(item["is_correct"] for item in unique.values())
    latest_correct = sum(item["is_correct"] for item in latest.values())
    return {
        "score": round(correct / count * 100, 1) if count else None,
        "latest_score": round(latest_correct / count * 100, 1) if count else None,
        "evidence_count": count,
        "correct": correct,
        "latest_correct": latest_correct,
        "attempt_count": len(items),
        "repeat_count": len(items) - count,
        "evidence_status": "unmeasured"
        if not count
        else "insufficient"
        if count < 2
        else "emerging"
        if count < 5
        else "stable",
        "confidence": min(1, count / 5),
        "source_question_ids": list(unique),
    }


def formal_records(submissions: dict) -> list[dict]:
    return sorted(
        (r for r in submissions.values()
         if r.get("provenance") != "legacy_answers"
         and r.get("kind") in {"assessment", "unit", "posttest"}),
        key=lambda r: r.get("created_at") or "",
    )


def latest_by_source(records: list[dict]) -> dict:
    return {
        item["source_question_id"]: (record, item)
        for record in records
        for item in record["items"]
    }


def latest_wrong(submissions: dict, quizzes: dict) -> dict:
    units = {
        (quiz["topic"], question["source_question_id"]): quiz_id.removeprefix("unit-")
        for quiz_id, quiz in quizzes.items() if quiz["kind"] == "unit"
        for question in quiz["questions"]
    }
    latest = latest_by_source(formal_records(submissions))
    wrong = sorted(source for source, (_, item) in latest.items() if not item["is_correct"])
    wrong.sort(key=lambda source: latest[source][0].get("created_at") or "", reverse=True)
    items = []
    for source in wrong[:10]:
        result, item = latest[source]
        items.append({
            **item,
            "submission_id": result["submission_id"],
            "quiz_id": result["quiz_id"],
            "topic_id": result["topic"],
            "unit_id": units.get((result["topic"], source)),
            "reason": "最近一次正式作答仍答错。",
            "last_submitted_at": result.get("created_at"),
            "practice_available": False,
        })
    return {
        "policy_version": "latest-wrong-v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "items": items,
    }


def build_profile(submissions: dict) -> dict:
    records = formal_records(submissions)
    items = [item for record in records for item in record["items"]]
    matrix = [
        {
            "dimension": dimension,
            "name": name,
            "cells": [
                {
                    "bloom": bloom,
                    "name": bloom_name,
                    **statistics(
                        [
                            item
                            for item in items
                            if item["dimension"] == dimension and item["bloom"] == bloom
                        ]
                    ),
                }
                for bloom, bloom_name in BLOOM.items()
            ],
            **statistics([item for item in items if item["dimension"] == dimension]),
        }
        for dimension, name in DIMENSIONS.items()
    ]
    knowledge = [
        {"name": category, **statistics([item for item in items if item["category"] == category])}
        for category in dict.fromkeys(item["category"] for item in items)
    ]
    weak = [item["name"] for item in knowledge if item["score"] < 70]
    return {
        "policy_version": PROFILE_VERSION,
        "matrix": matrix,
        "knowledge_points": knowledge,
        "submission_count": len(records),
        "has_review_items": any(
            not item["is_correct"] for _, item in latest_by_source(records).values()
        ),
        **statistics(items),
        "focus_areas": weak,
        "next_steps": [f"复习“{name}”的错题，再用不同例句练习。" for name in weak[:3]]
        or ["继续学习新的单元，补充不同题目的作答证据。"],
        "scope": (
            "分数为不同题目首次记录的正确率；最近练习表现另列。"
            "重复题和后测中的同题变序不增加证据覆盖。"
            "当前为文字选择题，证据数量充分不等于已掌握，不评定实际听说、书写或汉语等级。"
        ),
    }
