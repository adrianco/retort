defmodule BooksApi.Repo do
  use Ecto.Repo,
    otp_app: :books_api,
    adapter: Ecto.Adapters.SQLite3
end
