import Config

config :book_api, BookApi.Repo,
  database: Path.join(__DIR__, "../tmp/db/books_test.sqlite3"),
  priv: "priv/repo",
  pool: Ecto.Adapters.SQL.Sandbox,
  pool_size: 1,
  log: false

config :book_api, ecto_repos: [BookApi.Repo]

config :elixir, :time_zone_database, TimeZoneInfo.TimeZoneDatabase
