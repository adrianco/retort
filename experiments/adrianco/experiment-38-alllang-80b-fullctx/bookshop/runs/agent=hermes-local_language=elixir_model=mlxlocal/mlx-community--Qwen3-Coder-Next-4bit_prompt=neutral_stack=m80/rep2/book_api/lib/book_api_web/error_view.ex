defmodule BookApiWeb.ErrorView do
  use BookApiWeb, :view

  # By default, Phoenix returns the status message from
  # template not found errors.
  def render(template, _assigns) do
    %{
      errors: %{
        detail: Phoenix.Controller.status_message_from_template(template)
      }
    }
  end

  # In case of render errors, return a JSON response.
  def render("*.json", _assigns) do
    %{
      errors: %{
        detail: "Internal Server Error"
      }
    }
  end
end
