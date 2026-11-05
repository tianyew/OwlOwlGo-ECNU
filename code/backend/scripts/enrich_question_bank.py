"""Create an enriched, reviewable copy of the adult L2 Chinese question bank.

The source files are never modified.  Labels produced here are candidates generated
by transparent rules; they are not validated HSK/CEFR levels or gold annotations.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any


LABEL_SOURCE = "heuristic_v1"
CONTENT_VERSION = "2.0-enriched.2"
REVIEW_STATUS = "ai_reviewed_for_coursework"
REVIEW_METHOD = "rule_based_ai_assisted_review_v1"


def contains_any(text: str, words: tuple[str, ...]) -> bool:
    return any(word in text for word in words)


def candidate_l2_level(item: dict[str, Any]) -> str:
    """Keep this deliberately conservative: school grade is not an L2 level."""
    band = item.get("curriculum_band", "")
    return {
        "基础": "beginner_candidate",
        "进阶": "intermediate_candidate",
        "提高": "advanced_candidate",
    }.get(band, "unclassified")


def topic_ids(item: dict[str, Any]) -> list[str]:
    category = item.get("category", "")
    tags = str(item.get("derived", {}).get("topic_tags", ""))
    title = str(item.get("title", ""))
    text = f"{tags} {title}"
    topics: list[str] = []
    if category == "古诗文":
        topics.append("poetry")
    if category == "文言文":
        topics.append("classical_chinese")
    if contains_any(text, ("交通", "出行", "地铁", "旅游", "景点", "酒店")):
        topics.append("travel")
    if contains_any(text, ("校园", "学习", "课程", "图书馆", "校刊", "发言稿")):
        topics.append("campus")
    if contains_any(text, ("生活", "购物", "饮食", "健康", "安全", "天气", "社区")):
        topics.append("daily")
    if not topics:
        topics.append("general_reading")
    return list(dict.fromkeys(topics))


def question_type(prompt: str) -> str:
    if contains_any(prompt, ("判断", "对的画", "正确的打", "√", "×")):
        return "judgment"
    if contains_any(prompt, ("连一连", "匹配")):
        return "matching"
    if contains_any(prompt, ("断句", "用“/”", "用/")):
        return "segmentation"
    if contains_any(prompt, ("翻译成现代汉语", "翻译下列", "译成现代汉语")):
        return "translation"
    if contains_any(prompt, ("修改", "改正", "修改符号")):
        return "editing"
    if contains_any(prompt, ("选择", "哪一项", "下列", "（  ）", "(  )")) and contains_any(
        prompt, ("A.", "A．", "A、")
    ):
        return "single_choice"
    if contains_any(prompt, ("填空", "____", "解释下列", "意思是")):
        return "fill_or_short_answer"
    if contains_any(prompt, ("谈谈", "分析", "启示", "赏析", "理解", "看法", "为什么")):
        return "open_response"
    return "short_answer"


def cognitive_classification(prompt: str, q_type: str) -> tuple[str, float, str]:
    """Classify against Anderson & Krathwohl's six cognitive processes.

    The first matching, highest-order process wins.  This identifies the main
    observable operation requested by the item; it is not a claim that higher
    categories are always more difficult for every learner.
    """
    rules = [
        (
            "create",
            ("创作", "创编", "设计", "拟写", "续写", "仿写", "编写", "制定", "写一则", "写一封", "写一段", "写一篇"),
            "题目要求学习者产生、设计或组织新的语言作品。",
        ),
        (
            "evaluate",
            ("评价", "评析", "是否赞同", "是否同意", "你赞同", "你同意", "是否合理", "你认为", "谈看法", "谈观点"),
            "题目要求依据材料或标准作出判断并说明理由。",
        ),
        (
            "analyze",
            ("分析", "比较", "异同", "作用", "技巧", "论证", "原因", "为什么", "怎样进行论述", "人物形象"),
            "题目要求分解信息、比较关系或解释结构与原因。",
        ),
        (
            "apply",
            ("启示", "应该怎么", "你会怎么", "怎么办", "结合实际", "联系实际", "运用", "改写", "修改", "翻译", "断句"),
            "题目要求在具体情境中运用规则、方法或语言知识。",
        ),
        (
            "remember",
            ("默写", "背诵", "作者是", "出处是", "写出原句", "填入原句"),
            "题目主要要求提取或再认已学事实与原句。",
        ),
    ]
    for level, keywords, rationale in rules:
        matched = next((word for word in keywords if word in prompt), None)
        if matched:
            return level, 0.9, f"命中关键词“{matched}”。{rationale}"
    if q_type in {"translation", "editing", "segmentation"}:
        return "apply", 0.84, f"题型为 {q_type}，需要执行已学语言规则或转换程序。"
    if q_type == "open_response":
        return "analyze", 0.68, "开放作答通常需要组织文本证据；未命中更明确的评价或创造指令。"
    return "understand", 0.72, "题目主要要求解释、概括、分类或从材料中提取意义。"


def language_dimension(category: str, prompt: str, q_type: str) -> str:
    if q_type == "translation" or category == "文言文":
        return "classical_chinese_comprehension"
    if category == "古诗文":
        return "poetry_comprehension"
    if q_type == "editing":
        return "written_language_use"
    if category == "非连续性文本":
        return "multimodal_information_literacy"
    if category == "功能性文体":
        return "functional_reading"
    if contains_any(prompt, ("根据材料", "从文中", "信息")):
        return "information_retrieval"
    return "reading_comprehension"


def scaffold_levels(category: str, q_type: str) -> list[dict[str, Any]]:
    strategy = {
        "single_choice": "逐项对照材料，排除与原文信息不一致的选项。",
        "judgment": "把每个判断拆成关键词，再回到材料逐项核对。",
        "matching": "先确认每一项的核心特征，再寻找唯一对应关系。",
        "translation": "先圈出关键词和句式，再按现代汉语语序组织句子。",
        "segmentation": "先找谓语、人物和语气词，再判断句意停顿。",
        "editing": "分别检查用词、语序、成分和标点。",
        "open_response": "先写观点，再引用材料证据，最后说明二者关系。",
        "fill_or_short_answer": "根据题干限定范围，回到原文定位对应词句。",
        "short_answer": "先明确题目问什么，再从材料中寻找直接证据。",
    }[q_type]
    category_hint = {
        "非连续性文本": "注意标题、表格、图例、数字和不同材料之间的关系。",
        "功能性文体": "注意写作对象、目的、时间、地点和行动要求。",
        "古诗文": "先圈出景物、动作和情感词，再联系上下句。",
        "文言文": "结合上下文判断实词、虚词和省略成分，不要只按现代词义猜测。",
    }.get(category, "回到材料定位与问题最相关的句子。")
    return [
        {"level": 0, "kind": "none", "text": "不提供提示。"},
        {"level": 1, "kind": "orientation", "text": "再读一遍题干，圈出问题中的关键词。"},
        {"level": 2, "kind": "evidence", "text": category_hint},
        {"level": 3, "kind": "strategy", "text": strategy},
        {
            "level": 4,
            "kind": "worked_explanation",
            "text": "提交本次作答后显示参考答案与解析；开放题按评分要点对照。",
        },
    ]


def quality_flags(question: dict[str, Any], q_type: str) -> list[str]:
    prompt = str(question.get("prompt", ""))
    answer = str(question.get("answer", "")).strip()
    flags = ["candidate_l2_level_requires_empirical_calibration", "license_requires_verification"]
    if not answer:
        flags.append("missing_answer")
    if q_type == "single_choice":
        flags.append("options_embedded_in_prompt_require_normalization")
    if q_type == "open_response":
        flags.append("open_response_requires_scoring_rubric")
    if contains_any(prompt, ("（1）", "(1)", "①")):
        flags.append("multi_part_item")
    if len(prompt) > 500:
        flags.append("long_prompt_review_readability")
    return flags


def enrich_item(item: dict[str, Any]) -> dict[str, Any]:
    result = dict(item)
    result.update(
        {
            "l2_level": candidate_l2_level(item),
            "topic_ids": topic_ids(item),
            "review_status": REVIEW_STATUS,
            "review_method": REVIEW_METHOD,
            "license_status": "requires_verification",
            "content_version": CONTENT_VERSION,
            "label_source": LABEL_SOURCE,
        }
    )
    enriched_questions = []
    for question in item.get("questions", []):
        enriched = dict(question)
        prompt = str(question.get("prompt", ""))
        q_type = question_type(prompt)
        bloom_level, bloom_confidence, bloom_rationale = cognitive_classification(prompt, q_type)
        enriched.update(
            {
                "question_type": q_type,
                "cognitive_level": bloom_level,
                "bloom_level": bloom_level,
                "bloom_confidence": bloom_confidence,
                "bloom_rationale": bloom_rationale,
                "language_dimension": language_dimension(item.get("category", ""), prompt, q_type),
                "scaffold_levels": scaffold_levels(item.get("category", ""), q_type),
                "quality_flags": quality_flags(question, q_type),
                "review_status": REVIEW_STATUS,
                "review_method": REVIEW_METHOD,
                "license_status": "requires_verification",
                "adapted_from": question.get("question_id"),
                "content_version": CONTENT_VERSION,
                "label_source": LABEL_SOURCE,
            }
        )
        enriched_questions.append(enriched)
    result["questions"] = enriched_questions
    return result


def json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def add_column(connection: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    existing = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
    if column not in existing:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def enrich_sqlite(source: Path, destination: Path, items: list[dict[str, Any]]) -> None:
    shutil.copy2(source, destination)
    with sqlite3.connect(destination) as connection:
        for name in (
            "l2_level",
            "topic_ids",
            "review_status",
            "review_method",
            "license_status",
            "content_version",
            "label_source",
        ):
            add_column(connection, "passages", name, "TEXT")
        for name in (
            "question_type",
            "cognitive_level",
            "bloom_level",
            "bloom_confidence",
            "bloom_rationale",
            "language_dimension",
            "scaffold_levels",
            "quality_flags",
            "review_status",
            "review_method",
            "license_status",
            "adapted_from",
            "content_version",
            "label_source",
        ):
            add_column(connection, "questions", name, "TEXT")

        for item in items:
            connection.execute(
                """UPDATE passages SET l2_level=?, topic_ids=?, review_status=?, review_method=?,
                   license_status=?, content_version=?, label_source=? WHERE sample_id=?""",
                (
                    item["l2_level"],
                    json_text(item["topic_ids"]),
                    item["review_status"],
                    item["review_method"],
                    item["license_status"],
                    item["content_version"],
                    item["label_source"],
                    item["sample_id"],
                ),
            )
            for question in item["questions"]:
                connection.execute(
                    """UPDATE questions SET question_type=?, cognitive_level=?, bloom_level=?,
                       bloom_confidence=?, bloom_rationale=?, language_dimension=?,
                       scaffold_levels=?, quality_flags=?, review_status=?, review_method=?,
                       license_status=?, adapted_from=?, content_version=?, label_source=?
                       WHERE question_id=?""",
                    (
                        question["question_type"],
                        question["cognitive_level"],
                        question["bloom_level"],
                        str(question["bloom_confidence"]),
                        question["bloom_rationale"],
                        question["language_dimension"],
                        json_text(question["scaffold_levels"]),
                        json_text(question["quality_flags"]),
                        question["review_status"],
                        question["review_method"],
                        question["license_status"],
                        question["adapted_from"],
                        question["content_version"],
                        question["label_source"],
                        question["question_id"],
                    ),
                )
        connection.commit()


def report(items: list[dict[str, Any]]) -> str:
    questions = [question for item in items for question in item["questions"]]

    def section(title: str, values: list[str]) -> list[str]:
        lines = [f"## {title}", "", "| 标签 | 数量 |", "| --- | ---: |"]
        lines.extend(f"| {name} | {count} |" for name, count in Counter(values).most_common())
        lines.append("")
        return lines

    lines = [
        "# 题库自动增强报告",
        "",
        f"- 材料数：{len(items)}",
        f"- 小题数：{len(questions)}",
        f"- 标签规则：`{LABEL_SOURCE}`",
        f"- 审核方式：`{REVIEW_METHOD}`；状态：`{REVIEW_STATUS}`。",
        "- 自动审核适用于课程作业与原型，不代表专家效度审查或经过验证的 HSK、CEFR 难度。",
        "- 授权状态统一设为 `requires_verification`，公开部署前必须核查来源许可。",
        "",
    ]
    lines += section("二语难度候选", [item["l2_level"] for item in items])
    lines += section("题型", [q["question_type"] for q in questions])
    lines += section("修订版布鲁姆六层认知过程", [q["bloom_level"] for q in questions])
    lines += section("语言能力维度", [q["language_dimension"] for q in questions])
    lines += [
        "## 后续研究与系统使用建议",
        "",
        "1. 自动出题时优先检索 `adult_relevance_band=高` 且主题属于 travel、daily、campus 的材料。",
        "2. 用真实学习者作答数据校正二语难度；中小学年级不能直接映射 HSK/CEFR。",
        "3. 将题干中的选项拆分成结构化 `options`，开放题补充评分量规。",
        "4. 为入选题编写题目专属提示，替换当前通用支架文本。",
        "5. 确认授权后再把 `license_status` 改为允许发布的状态。",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_dir", type=Path, help="Directory containing the original JSON/SQLite files")
    parser.add_argument("--output-dir", type=Path, help="Destination; defaults to <source_dir>/enriched")
    args = parser.parse_args()
    source_dir = args.source_dir.resolve()
    output_dir = (args.output_dir or source_dir / "enriched").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    source_json = source_dir / "成人二语汉语学习抽样题库_700篇.json"
    source_sqlite = source_dir / "成人二语汉语学习抽样题库_700篇.sqlite"
    data = json.loads(source_json.read_text(encoding="utf-8"))
    items = [enrich_item(item) for item in data["items"]]
    data["items"] = items
    data["enrichment"] = {
        "version": CONTENT_VERSION,
        "label_source": LABEL_SOURCE,
        "review_method": REVIEW_METHOD,
        "status": REVIEW_STATUS,
    }

    output_json = output_dir / "成人二语汉语学习抽样题库_700篇_增强版.json"
    output_sqlite = output_dir / "成人二语汉语学习抽样题库_700篇_增强版.sqlite"
    output_report = output_dir / "增强字段与标签报告.md"
    output_json.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    enrich_sqlite(source_sqlite, output_sqlite, items)
    output_report.write_text(report(items), encoding="utf-8")
    print(f"Wrote {output_json}")
    print(f"Wrote {output_sqlite}")
    print(f"Wrote {output_report}")


if __name__ == "__main__":
    main()

