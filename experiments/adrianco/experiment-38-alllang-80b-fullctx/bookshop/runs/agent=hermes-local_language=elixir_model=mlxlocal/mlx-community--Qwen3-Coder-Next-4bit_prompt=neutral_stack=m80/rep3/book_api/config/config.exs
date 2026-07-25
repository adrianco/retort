import Config

# This file is responsible for configuring your application
# and its dependencies with the aid of the Config module.

# General application configuration
config :book_api,
  ecto_repos: [BookAPI.Repo],
  generators: [context_app: :book_api]

# Configures the database
config :book_api, BookAPI.Repo,
  database: "book_api.db",
  show_sensitive_data_on_connection_error: true,
  pool_size: 10

# Size in megabytes of the database pool
config :book_api, :pool_size, 10

# Import environment specific config. This must remain at the bottom
# of this file so it overrides the configuration defined above.
import_config "#{config_env()}.exs"
