defmodule BookApiWeb.HealthController do
  use BookApiWeb, :controller

  def health(conn, _params) do
    render(conn, :health)
  end
end
