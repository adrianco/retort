import Config

# For production, we configure the database
config :book_api, BookAPI.Repo,
  database: "book_api_prod.db",
  show_sensitive_data_on_connection_error: true,
  pool_size: 10
