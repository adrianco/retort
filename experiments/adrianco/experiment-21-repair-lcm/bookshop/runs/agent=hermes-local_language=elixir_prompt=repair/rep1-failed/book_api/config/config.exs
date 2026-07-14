import Config

config :book_api, BookApi.Repo,
  database: Path.join(__DIR__, "../tmp/db/books_dev.sqlite3"),
  priv: "priv/repo",
  pool: Ecto.Adapters.SQL.Sandbox,
  pool_size: 10

config :book_api, ecto_repos: [BookApi.Repo]
