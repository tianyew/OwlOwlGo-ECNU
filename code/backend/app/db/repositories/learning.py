"""User-owned progress documents with optimistic concurrency and atomic writes."""

import json
from datetime import UTC, datetime

from app.db.repositories.accounts import JsonAccountRepository
from app.schemas.learning import PROMPT_VERSION, LearningState, fingerprint


class ProgressConflict(Exception):
    pass


class JsonLearningRepository(JsonAccountRepository):
    def _read(self):
        if not self.path.exists():
            return {"schema_version": 1, "progress": {}}
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if data.get("schema_version") != 1 or not isinstance(data.get("progress"), dict):
            raise ValueError("Invalid learning file")
        # Older saved plans predate explicit setup completion.
        for record in data["progress"].values():
            state = record["state"]
            state.setdefault("onboarding_complete", state.get("stage") == "plan")
            if (
                record.get("analysis")
                and record["analysis"].get("prompt_version") != PROMPT_VERSION
            ):
                record["analysis"] = None
        return data

    @staticmethod
    def empty():
        return {
            "revision": 0,
            "state": LearningState().model_dump(),
            "updated_at": None,
            "analysis": None,
        }

    def get(self, user_id):
        with self.lock:
            return self._read()["progress"].get(user_id, self.empty())

    def save(self, user_id, state, revision):
        with self.lock:
            data = self._read()
            previous = data["progress"].get(user_id, self.empty())
            if previous["revision"] != revision:
                raise ProgressConflict
            record = {
                "revision": revision + 1,
                "state": state,
                "updated_at": datetime.now(UTC).isoformat(),
                "analysis": previous["analysis"]
                if fingerprint(previous["state"]) == fingerprint(state)
                else None,
            }
            data["progress"][user_id] = record
            self._write(data)
            return record

    def save_analysis(self, user_id, source, analysis):
        with self.lock:
            data = self._read()
            record = data["progress"].get(user_id, self.empty())
            if fingerprint(record["state"]) != source:
                raise ProgressConflict
            record["analysis"] = analysis
            data["progress"][user_id] = record
            self._write(data)
            return analysis
