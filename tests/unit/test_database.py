"""Engine configuration + concurrency-safe table creation for sharded runs."""
from __future__ import annotations


def test_engine_sets_busy_timeout(tmp_path):
    # Without a busy timeout, concurrent shards lose writes to "database is locked".
    from retort.storage.database import get_engine

    engine = get_engine(tmp_path / "t.db")
    with engine.connect() as conn:
        busy = conn.exec_driver_sql("PRAGMA busy_timeout").scalar()
    assert busy is not None and int(busy) >= 1000


def test_engine_uses_wal(tmp_path):
    from retort.storage.database import get_engine

    engine = get_engine(tmp_path / "t.db")
    with engine.connect() as conn:
        mode = conn.exec_driver_sql("PRAGMA journal_mode").scalar()
    assert str(mode).lower() == "wal"


def test_create_tables_idempotent(tmp_path):
    from retort.storage.database import create_tables, get_engine

    engine = get_engine(tmp_path / "t.db")
    create_tables(engine)
    create_tables(engine)  # second call must not raise


def test_create_tables_retries_past_concurrent_already_exists(tmp_path, monkeypatch):
    # Simulate the cold-start shard race: a peer process created the table just
    # before us, so the first create_all raises "already exists"; create_tables
    # must swallow it and retry to success rather than crash the shard.
    from sqlalchemy.exc import OperationalError

    from retort.storage import database

    real = database.Base.metadata.create_all
    calls = {"n": 0}

    def flaky_create_all(engine, *args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise OperationalError(
                "CREATE TABLE factor_levels (...)",
                {},
                Exception("table factor_levels already exists"),
            )
        return real(engine, *args, **kwargs)

    monkeypatch.setattr(database.Base.metadata, "create_all", flaky_create_all)
    engine = database.get_engine(tmp_path / "t.db")
    database.create_tables(engine)
    assert calls["n"] >= 2
