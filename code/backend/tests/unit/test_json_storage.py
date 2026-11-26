"""A failed atomic replacement must preserve both account and learning data."""

import pytest

from app.db.repositories.accounts import JsonAccountRepository
from app.db.repositories.learning import JsonLearningRepository
from app.schemas.learning import LearningState


@pytest.mark.parametrize("kind", ["accounts", "learning"])
def test_failed_write_keeps_previous_data_and_allows_retry(tmp_path, monkeypatch, kind):
    path = tmp_path / f"{kind}.json"
    if kind == "accounts":
        repo = JsonAccountRepository(path)
        repo.create_user({"_id": "first", "username": "first"})

        def save():
            repo.create_user({"_id": "second", "username": "second"})

        def verify():
            assert repo.find_user("first") is not None
            assert repo.find_user("second") is not None
    else:
        repo = JsonLearningRepository(path)
        state = LearningState().model_dump()
        repo.save("first", state, 0)

        def save():
            repo.save("first", state, 1)

        def verify():
            assert repo.get("first")["revision"] == 2

    original = path.read_bytes()

    def fail_replace(*args):
        raise OSError("simulated filesystem failure")

    with monkeypatch.context() as patch:
        patch.setattr("app.db.json_store.os.replace", fail_replace)
        with pytest.raises(OSError, match="simulated filesystem failure"):
            save()
    assert path.read_bytes() == original
    assert not list(tmp_path.glob(".*.tmp"))
    save()
    verify()
