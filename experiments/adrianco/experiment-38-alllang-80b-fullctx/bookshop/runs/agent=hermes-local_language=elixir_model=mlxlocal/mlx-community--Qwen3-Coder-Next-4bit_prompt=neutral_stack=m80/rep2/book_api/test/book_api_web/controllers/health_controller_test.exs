defmodule BookApiWeb.HealthControllerTest do
  use BookApiWeb.ConnCase, async: true

  test "health check returns ok", %{conn: conn} do
    conn = get(conn, ~p"/api/health")
    assert json_response(conn, 200) == %{"status" => "ok", "service" => "book-api"}
  end
end
