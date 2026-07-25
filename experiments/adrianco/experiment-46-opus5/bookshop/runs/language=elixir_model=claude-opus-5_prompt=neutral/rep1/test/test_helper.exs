# `mix test` has already started the application, and with it BookApi.Repo, so
# migrate through that connection rather than restarting the repo in a separate
# mix task. The database file itself is created by SQLite on first connect.
Ecto.Migrator.run(BookApi.Repo, :up, all: true, log: false)

Ecto.Adapters.SQL.Sandbox.mode(BookApi.Repo, :manual)
ExUnit.start()
