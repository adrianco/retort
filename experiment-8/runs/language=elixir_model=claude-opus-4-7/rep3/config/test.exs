import Config

config :book_api, BookApi.Repo,
  database: Path.expand("../book_api_test.db", __DIR__),
  pool: Ecto.Adapters.SQL.Sandbox

config :logger, level: :warning

config :book_api, start_server: false
