import Config

config :book_api, BookApi.Repo,
  database: Path.expand("../book_api_test.db", __DIR__),
  pool: Ecto.Adapters.SQL.Sandbox,
  pool_size: 5

config :book_api, port: 4001

config :logger, level: :warning
