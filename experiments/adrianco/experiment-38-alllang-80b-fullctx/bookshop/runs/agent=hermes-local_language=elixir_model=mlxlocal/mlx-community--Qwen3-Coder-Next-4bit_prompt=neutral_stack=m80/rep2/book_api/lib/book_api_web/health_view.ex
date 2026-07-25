defmodule BookApiWeb.HealthView do
  use BookApiWeb, :view

  def render("health.json", _assigns) do
    %{status: "ok", service: "book-api"}
  end
end
