defmodule BookApiWeb.HealthController do
  use BookApiWeb, :controller

  def index(conn, _params) do
    json(conn, %{status: "healthy"})
  end
end
