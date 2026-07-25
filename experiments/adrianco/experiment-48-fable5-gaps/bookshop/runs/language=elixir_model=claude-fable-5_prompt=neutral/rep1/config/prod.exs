import Config

config :books_api, port: String.to_integer(System.get_env("PORT") || "4000")
