config :book_api, BookApi.Repo,
  database: "book_api_test.db",
  adapter: Ecto.Adapters.SQL,
  pool: Ecto.Adapters.SQL.Sandbox

config :book_api, BookApiWeb.Endpoint,
  http: [ip: {127, 0, 0, 1}, port: 4001],
  url: [host: "localhost", port: 4001],
  secret_key_base: "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6",
  server: false,
  cache_static_manifest: "priv/static/cache_manifest.json",
  debug_errors: true,
  check_origin: false
