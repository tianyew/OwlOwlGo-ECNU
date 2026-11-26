"""Assessment evidence and cache identity, independent of transport and providers."""

import hashlib
import json

from app.domain.content.catalog import get_quiz

ITEMS = get_quiz("assessment")["questions"]
KEY = [item["answer"] for item in ITEMS]
CATEGORIES = [("拼音基础", [0, 1]), ("四声辨识", [2, 3, 4]), ("基础变调", [5, 6, 7])]


def evidence(state: dict, prompt_version: str) -> dict:
    answers = state["quiz"]["answers"]
    return {
        "prompt_version": prompt_version,
        "items": [
            {
                "question_id": q["id"],
                "knowledge_point": q["category"],
                "prompt": q["prompt"],
                "example": q["example"],
                "options": q["options"],
                "selected_index": answers[i],
                "selected_answer": q["options"][answers[i]],
                "correct_index": q["answer"],
                "correct_answer": q["options"][q["answer"]],
                "is_correct": answers[i] == q["answer"],
                "explanation": q["explanation"],
            }
            for i, q in enumerate(ITEMS)
            if i < len(answers)
        ],
        "score": int(sum(a == KEY[i] for i, a in enumerate(answers)) / len(KEY) * 100 + 0.5),
        "scope": "固定8题拼音与声调文字辨识，不代表正式汉语等级或口语水平",
        "answered": len(answers),
        "correct": sum(a == KEY[i] for i, a in enumerate(answers)),
        "dimensions": [
            {
                "name": name,
                "total": len(indices),
                "correct": sum(i < len(answers) and answers[i] == KEY[i] for i in indices),
            }
            for name, indices in CATEGORIES
        ],
    }


def fingerprint(state: dict, prompt_version: str) -> str:
    payload = json.dumps(evidence(state, prompt_version), sort_keys=True).encode()
    return hashlib.sha256(payload).hexdigest()
