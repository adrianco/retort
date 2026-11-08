defmodule BookCollection.Repo do
  use Ecto.Repo, otp_app: :book_collection, adapter: Ecto.Adapters.SQLite3
end
