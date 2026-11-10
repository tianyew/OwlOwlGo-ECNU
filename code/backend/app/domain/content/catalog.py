"""Single versioned source for lessons, assessments and objective scoring."""

import json
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CATALOG = json.loads((ROOT / "curriculum.json").read_text(encoding="utf-8"))
ASSESSMENT = json.loads((ROOT.parent / "learner/assessment_items.json").read_text("utf-8"))
CONTENT_VERSION = CATALOG["content_version"]
SCORING_VERSION = "objective-v2"
TOPIC_IDS = tuple(topic["id"] for topic in CATALOG["topics"])
QUIZZES = {
    "assessment": {
        "id": "assessment",
        "kind": "assessment",
        "title": "拼音与声调前测",
        "topic": None,
        "unit_index": None,
        "questions": [
            {
                **q,
                "source_question_id": q["id"],
                "dimension": "phonetics",
                "bloom": "apply" if i >= 5 else "remember" if i in (2, 3, 4) else "understand",
            }
            for i, q in enumerate(ASSESSMENT)
        ],
    }
}
for topic in CATALOG["topics"]:
    for index, unit in enumerate(topic["units"]):
        quiz_id = f"unit-{topic['id']}-{index}"
        QUIZZES[quiz_id] = {
            "id": quiz_id,
            "kind": "unit",
            "title": unit["title"] + " · 单元小测",
            "topic": topic["id"],
            "unit_index": index,
            "questions": unit["quiz"],
        }
    quiz_id = f"post-{topic['id']}"
    QUIZZES[quiz_id] = {
        "id": quiz_id,
        "kind": "posttest",
        "title": topic["title"] + " · 方向后测",
        "topic": topic["id"],
        "unit_index": None,
        "questions": topic["posttest"],
    }


def get_quiz(quiz_id: str) -> dict:
    if quiz_id not in QUIZZES:
        raise KeyError("测验不存在。")
    return QUIZZES[quiz_id]


def public_catalog() -> dict:
    topics = deepcopy(CATALOG["topics"])
    for topic in topics:
        topic.pop("posttest")
        topic["posttest_id"] = f"post-{topic['id']}"
        topic["schedule"] = (
            "建议分 5 次学习，每次 20–25 分钟：认读词句 → 情境对话 → 迁移练习 → 单元小测。"
            "次日复习错题，完成方向学习后进行后测。"
        )
        for index, unit in enumerate(topic["units"]):
            unit.pop("quiz")
            unit["quiz_id"] = f"unit-{topic['id']}-{index}"
    return {"content_version": CONTENT_VERSION, "topics": topics}


def public_questions(quiz_id: str) -> list[dict]:
    return [
        {
            key: deepcopy(value)
            for key, value in q.items()
            if key not in {"answer", "explanation", "source_question_id", "dimension", "bloom"}
        }
        for q in get_quiz(quiz_id)["questions"]
    ]


def validate_answers(quiz_id: str, answers: dict[str, int], *, complete: bool = True):
    questions = {q["id"]: q for q in get_quiz(quiz_id)["questions"]}
    if not set(answers) <= questions.keys() or (complete and set(answers) != questions.keys()):
        raise ValueError("请按当前测验的题目完整作答。")
    for question_id, index in answers.items():
        if type(index) is not int or not 0 <= index < len(questions[question_id]["options"]):
            raise ValueError("答案选项无效，请重新作答。")


def grade(quiz_id: str, answers: dict[str, int]) -> dict:
    validate_answers(quiz_id, answers)
    quiz = get_quiz(quiz_id)
    items = [
        {
            **{key: deepcopy(value) for key, value in q.items() if key not in {"id", "answer"}},
            "question_id": q["id"],
            "selected_index": answers[q["id"]],
            "correct_index": q["answer"],
            "is_correct": answers[q["id"]] == q["answer"],
        }
        for q in quiz["questions"]
    ]
    correct = sum(item["is_correct"] for item in items)
    score = (correct * 200 + len(items)) // (2 * len(items))
    return {
        "quiz_id": quiz_id,
        "kind": quiz["kind"],
        "topic": quiz["topic"],
        "unit_index": quiz["unit_index"],
        "content_version": CONTENT_VERSION,
        "scoring_version": SCORING_VERSION,
        "score": score,
        "correct": correct,
        "total": len(items),
        "passed": True
        if quiz["kind"] == "assessment"
        else correct == len(items)
        if quiz["kind"] == "unit"
        else score >= 60,
        "items": items,
    }
