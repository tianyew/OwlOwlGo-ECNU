"""Atomic submissions, derived progress and replayable learner evidence."""

import json
from copy import deepcopy
from datetime import UTC, datetime

from app.db.repositories.accounts import JsonAccountRepository
from app.domain.content.catalog import CONTENT_VERSION, TOPIC_IDS, get_quiz, grade, validate_answers
from app.domain.learner.profile import build_profile
from app.schemas.learning import PROMPT_VERSION, LearningState, fingerprint


class ProgressConflict(Exception):
    pass


class UnitSubmissionConflict(Exception):
    pass


def latest_results(record):
    results = {}
    for result in record.get("submissions", {}).values():
        if result["kind"] == "assessment" and result.get("epoch", 0) != record["assessment_epoch"]:
            continue
        results[result["quiz_id"]] = result
    return results


def analysis_source(record):
    assessment = latest_results(record).get("assessment", {})
    identity = f"{assessment.get('submission_id')}:{record['assessment_epoch']}"
    return f"{identity}:{fingerprint(record['state'])}"


class JsonLearningRepository(JsonAccountRepository):
    @staticmethod
    def migrate(record):
        if record.get("authority_version") == 2:
            return
        state = record["state"]
        record["legacy_progress"] = deepcopy(state)
        record["authority_version"] = 2
        record["assessment_epoch"] = 0
        submissions = record.setdefault("submissions", {})
        quiz = state.get("quiz", {})
        if state.get("content_version") == 1 and quiz.get("stage") == "quiz":
            questions = get_quiz("assessment")["questions"]
            choices = {
                q["id"]: answer
                for q, answer in zip(questions, quiz.get("answers", []), strict=False)
            }
            current = quiz.get("current", 0)
            if type(current) is int and 0 <= current < len(questions):
                if quiz.get("selected") is not None:
                    choices[questions[current]["id"]] = quiz["selected"]
                try:
                    validate_answers("assessment", choices, complete=False)
                    state.setdefault("drafts", {}).setdefault(
                        "assessment",
                        {
                            "content_version": 1,
                            "current": current,
                            "answers": [
                                {"question_id": key, "selected_index": value}
                                for key, value in choices.items()
                            ],
                        },
                    )
                except ValueError:
                    pass
        if state.get("content_version") == 1 and quiz.get("stage") == "result":
            questions = get_quiz("assessment")["questions"]
            answers = quiz.get("answers", [])
            if len(answers) == len(questions):
                try:
                    result = grade(
                        "assessment",
                        {q["id"]: answer for q, answer in zip(questions, answers, strict=True)},
                    )
                    result.update(
                        submission_id="legacy-assessment",
                        epoch=0,
                        created_at=record.get("updated_at"),
                        provenance="legacy_answers",
                    )
                    submissions["legacy-assessment"] = result
                except ValueError:
                    pass
        for submission_id, old in record.pop("unit_submissions", {}).items():
            if old.get("content_version") != CONTENT_VERSION:
                continue
            result = grade(
                "unit-travel-0",
                {item["question_id"]: item["selected_index"] for item in old["items"]},
            )
            result.update(
                submission_id=submission_id,
                epoch=0,
                created_at=old["created_at"],
                provenance="pilot",
            )
            submissions[submission_id] = result

    @staticmethod
    def normalize(record):
        state = record["state"]
        results = latest_results(record)
        completed = {topic: set() for topic in TOPIC_IDS}
        for result in record["submissions"].values():
            if result["kind"] == "unit" and result["passed"]:
                completed[result["topic"]].add(result["unit_index"])
        state["completed"] = {topic: sorted(indices) for topic, indices in completed.items()}
        state["checks"] = {}
        state["posttests"] = {}
        state.setdefault("drafts", {})
        assessment = results.get("assessment")
        if assessment:
            answers = [item["selected_index"] for item in assessment["items"]]
            state["quiz"] = {
                "stage": "result",
                "current": 7,
                "selected": answers[-1],
                "submitted": True,
                "answers": answers,
            }
        else:
            state["quiz"] = LearningState().quiz.model_dump()
            state.update(stage="assessment", topic=None, onboarding_complete=False)
            record["analysis"] = None
        for result in results.values():
            attempt = {
                "answers": [item["selected_index"] for item in result["items"]],
                "submitted": True,
            }
            if result["kind"] == "unit":
                state["checks"][f"{result['topic']}:{result['unit_index']}"] = attempt
            elif result["kind"] == "posttest":
                state["posttests"][result["topic"]] = attempt
        return record

    def _read(self):
        if not self.path.exists():
            return {"schema_version": 1, "progress": {}}
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if data.get("schema_version") != 1 or not isinstance(data.get("progress"), dict):
            raise ValueError("Invalid learning file")
        for record in data["progress"].values():
            state = record["state"]
            state.setdefault("onboarding_complete", state.get("stage") == "plan")
            self.migrate(record)
            self.normalize(record)
            if (
                record.get("analysis")
                and record["analysis"].get("prompt_version") != PROMPT_VERSION
            ):
                record["analysis"] = None
        return data

    @staticmethod
    def empty():
        return {
            "authority_version": 2,
            "assessment_epoch": 0,
            "submissions": {},
            "revision": 0,
            "state": LearningState().model_dump(),
            "updated_at": None,
            "analysis": None,
        }

    def get(self, user_id):
        with self.lock:
            return self._read()["progress"].get(user_id, self.normalize(self.empty()))

    def save(self, user_id, state, revision):
        with self.lock:
            data = self._read()
            previous = data["progress"].get(user_id, self.empty())
            if previous["revision"] != revision:
                raise ProgressConflict
            record = {
                **previous,
                "revision": revision + 1,
                "state": state,
                "updated_at": datetime.now(UTC).isoformat(),
            }
            self.normalize(record)
            data["progress"][user_id] = record
            self._write(data)
            return record

    def submit_quiz(self, user_id, quiz_id, submission_id, version, answers, revision):
        if version != CONTENT_VERSION:
            raise UnitSubmissionConflict("题目版本已更新，请重新加载测验。")
        result = grade(quiz_id, answers)
        with self.lock:
            data = self._read()
            record = data["progress"].get(user_id, self.normalize(self.empty()))
            submissions = record["submissions"]
            if submission_id in submissions:
                old = submissions[submission_id]
                if any(old.get(key) != value for key, value in result.items()):
                    raise UnitSubmissionConflict("同一次提交不能更改测验或答案，请重新练习。")
                if result["kind"] == "assessment" and old["epoch"] != record["assessment_epoch"]:
                    raise UnitSubmissionConflict("这次前测已结束，请重新加载测验。")
                return {"result": old, "progress": record}
            if record["revision"] != revision:
                raise ProgressConflict
            state = record["state"]
            active = latest_results(record)
            if result["kind"] == "assessment":
                if "assessment" in active:
                    raise ValueError("本次前测已经提交，请使用重新测评入口开始新一轮。")
            elif "assessment" not in active or state["topic"] != result["topic"]:
                raise ValueError("请先完成前测并确认当前测验对应的学习方向。")
            result.update(
                submission_id=submission_id,
                epoch=record["assessment_epoch"],
                created_at=datetime.now(UTC).isoformat(),
                provenance="server",
            )
            previous_fingerprint = fingerprint(state)
            submissions[submission_id] = result
            state["drafts"].pop(quiz_id, None)
            self.normalize(record)
            if fingerprint(state) != previous_fingerprint:
                record["analysis"] = None
            record["revision"] += 1
            record["updated_at"] = result["created_at"]
            data["progress"][user_id] = record
            self._write(data)
            return {"result": result, "progress": record}

    def submit_unit(self, user_id, submission_id, version, answers, revision):
        return self.submit_quiz(user_id, "unit-travel-0", submission_id, version, answers, revision)

    def reset_assessment(self, user_id, revision):
        with self.lock:
            data = self._read()
            record = data["progress"].get(user_id, self.normalize(self.empty()))
            if record["revision"] != revision:
                raise ProgressConflict
            record["assessment_epoch"] += 1
            record["state"]["drafts"].pop("assessment", None)
            record["analysis"] = None
            self.normalize(record)
            record["revision"] += 1
            record["updated_at"] = datetime.now(UTC).isoformat()
            data["progress"][user_id] = record
            self._write(data)
            return record

    def public_progress(self, user_id):
        return self.without_unit_history(self.get(user_id))

    @staticmethod
    def without_unit_history(record):
        results = latest_results(record)
        completed = record["state"]["completed"]
        return deepcopy(
            {
                **{key: record[key] for key in ("revision", "state", "updated_at", "analysis")},
                "results": results,
                "profile": build_profile(record["submissions"]),
                "topic_completion": {
                    topic: len(completed.get(topic, [])) == 5
                    and any(
                        result["quiz_id"] == f"post-{topic}" and result["passed"]
                        for result in record["submissions"].values()
                    )
                    for topic in TOPIC_IDS
                },
            }
        )

    def save_analysis(self, user_id, source, analysis):
        with self.lock:
            data = self._read()
            record = data["progress"].get(user_id, self.normalize(self.empty()))
            if "assessment" not in latest_results(record) or analysis_source(record) != source:
                raise ProgressConflict
            record["analysis"] = analysis
            data["progress"][user_id] = record
            self._write(data)
            return analysis
