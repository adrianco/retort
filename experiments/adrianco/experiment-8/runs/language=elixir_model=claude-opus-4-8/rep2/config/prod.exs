import Config

config :book_api, port: String.to_integer(System.get_env("PORT") || "4000")
