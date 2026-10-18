import Config

config :book_api, BookApi.Repo,
  database: Path.expand("../book_api_test.db", __DIR__),
  pool_size: 1

config :book_api, :http_port, 4002
config :book_api, :start_server, false
config :logger, level: :warning
