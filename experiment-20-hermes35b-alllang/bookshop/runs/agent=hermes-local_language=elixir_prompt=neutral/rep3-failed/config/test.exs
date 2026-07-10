import Config

config :book_api, ecto_repos: [BookApi.Repo]

config :book_api, BookApi.Repo,
  adapter: Ecto.Adapters.SQLite3,
  database: Path.expand("../book_api_test.sqlite3", __DIR__)

config :book_api, BookApiWeb.Endpoint,
  http: [port: 4001],
  secret_key_base: "dummy_secret_key_base_for_phx_test_endpoint_123456",
  server: false,
  render_errors: [format: "json", encoder: Jason]

config :book_api, BookApiWeb.Endpoint,
  pubsub_server: BookApi.PubSub,
  live_view: [signing_salt: "dummysigningsalt"]
