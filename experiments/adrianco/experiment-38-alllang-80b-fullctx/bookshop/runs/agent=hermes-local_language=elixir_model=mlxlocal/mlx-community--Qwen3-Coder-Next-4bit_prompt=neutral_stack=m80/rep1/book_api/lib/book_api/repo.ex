defmodule BookApi.Repo do
  use Ecto.Repo,
    otp_app: :book_api,
    adapter: Ecto.Adapters.SQLite3

  def init(_, config) do
    {:ok, Keyword.put(config, :database, "priv/repo/book_api.db")}
  end
end
