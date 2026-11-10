"""Replayable evidence summaries; repeated questions do not create new coverage."""

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


def build_profile(submissions: dict) -> dict:
    # Legacy client snapshots remain traceable but are not verified profile evidence.
    records = [r for r in submissions.values() if r.get("provenance") != "legacy_answers"]
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
