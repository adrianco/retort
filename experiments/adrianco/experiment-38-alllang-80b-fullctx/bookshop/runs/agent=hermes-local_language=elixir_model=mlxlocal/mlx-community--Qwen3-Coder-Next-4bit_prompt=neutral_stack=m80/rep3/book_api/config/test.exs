import Config

# For test, we use a separate database
config :book_api, BookAPI.Repo,
  database: "book_api_test.db",
  show_sensitive_data_on_connection_error: true,
  pool_size: 10
