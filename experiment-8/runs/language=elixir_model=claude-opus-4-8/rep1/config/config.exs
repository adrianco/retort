import Config

config :book_api,
  ecto_repos: [BookApi.Repo],
  env: config_env()

config :book_api, BookApi.Repo,
  database: Path.expand("../priv/book_api_#{config_env()}.db", __DIR__),
  pool_size: 5,
  # SQLite is a single-writer DB; WAL + a busy timeout avoid transient
  # "database is locked" errors under concurrent connections.
  journal_mode: :wal,
  busy_timeout: 5_000

config :book_api, :port, 4000

import_config "#{config_env()}.exs"
