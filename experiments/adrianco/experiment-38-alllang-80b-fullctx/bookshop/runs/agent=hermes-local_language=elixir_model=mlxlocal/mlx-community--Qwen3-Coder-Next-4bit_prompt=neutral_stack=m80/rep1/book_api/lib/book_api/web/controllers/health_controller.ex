defmodule BookApi.Web.HealthController do
  use BookApi.Web, :controller

  def index(conn, _params) do
    conn
    |> put_status(:ok)
    |> json(%{status: "healthy"})
  end
end
