defmodule Books.Repo do
  use Ecto.Repo, otp_app: :books, adapter: Ecto.Adapters.SQLite3
end
