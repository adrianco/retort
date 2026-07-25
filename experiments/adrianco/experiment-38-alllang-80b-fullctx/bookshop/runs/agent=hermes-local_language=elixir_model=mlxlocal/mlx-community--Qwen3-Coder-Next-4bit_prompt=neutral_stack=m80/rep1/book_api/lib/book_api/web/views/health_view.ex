defmodule BookApi.Web.HealthView do
  use BookApi.Web, :view

  def render("index.json", %{status: status}) do
    %{status: status}
  end
end
