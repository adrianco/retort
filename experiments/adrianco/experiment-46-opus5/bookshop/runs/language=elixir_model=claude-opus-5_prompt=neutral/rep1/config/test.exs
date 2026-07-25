import Config

config :book_api, BookApi.Repo,
  database: Path.expand("../priv/book_api_test.db", __DIR__),
  pool: Ecto.Adapters.SQL.Sandbox,
  pool_size: 5

# The HTTP server is not started in tests; requests are driven through
# Plug.Test against BookApi.Router directly.
config :book_api, start_server: false

config :logger, level: :warning
