import Config

# Run each test in an isolated sandbox transaction so the suite is repeatable.
config :book_api, BookApi.Repo,
  database: Path.expand("../priv/book_api_test.db", __DIR__),
  pool: Ecto.Adapters.SQL.Sandbox,
  pool_size: 5

# Use a random free port for the test endpoint (we test the router directly).
config :book_api, :port, 0

# Keep test output readable.
config :logger, level: :warning
