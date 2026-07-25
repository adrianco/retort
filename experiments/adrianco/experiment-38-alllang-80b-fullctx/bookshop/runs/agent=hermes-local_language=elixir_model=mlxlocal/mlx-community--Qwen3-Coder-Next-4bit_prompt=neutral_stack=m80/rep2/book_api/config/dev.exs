config :book_api, BookApi.Repo,
  database: "book_api_dev.db",
  adapter: Ecto.Adapters.SQL,
  pool_size: 10

config :book_api, BookApiWeb.Endpoint,
  http: [ip: {127, 0, 0, 1}, port: 4000],
  url: [host: "localhost", port: 4000],
  secret_key_base: "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6",
  check_origin: false,
  code_reloader: true,
  debug_errors: true,
  render_errors: [view: BookApiWeb.ErrorView, accepts: ~w(json), layout: false],
  pubsub_server: BookApi.PubSub
