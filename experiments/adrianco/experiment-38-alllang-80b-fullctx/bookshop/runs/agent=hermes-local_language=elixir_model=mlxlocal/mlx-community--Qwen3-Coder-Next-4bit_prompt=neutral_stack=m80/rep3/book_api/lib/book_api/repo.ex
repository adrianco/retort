defmodule BookAPI.Repo do
  use Ecto.Repo,
    otp_app: :book_api,
    adapter: Ecto.Adapters.SQLite3
end
