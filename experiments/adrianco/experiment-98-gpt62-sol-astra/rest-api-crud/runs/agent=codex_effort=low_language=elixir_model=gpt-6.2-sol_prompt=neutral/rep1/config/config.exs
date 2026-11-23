import Config

config :book_collection,
  database: if(config_env() == :test, do: ":memory:", else: "book_collection.sqlite3"),
  server: config_env() != :test
