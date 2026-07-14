import Config

config :book_api, BookApi.Repo,
  database: Path.expand("../priv/book_api_test.db", __DIR__),
  pool: Ecto.Adapters.SQL.Sandbox,
  pool_size: 5,
  journal_mode: :wal,
  busy_timeout: 5000

config :logger, level: :warning
