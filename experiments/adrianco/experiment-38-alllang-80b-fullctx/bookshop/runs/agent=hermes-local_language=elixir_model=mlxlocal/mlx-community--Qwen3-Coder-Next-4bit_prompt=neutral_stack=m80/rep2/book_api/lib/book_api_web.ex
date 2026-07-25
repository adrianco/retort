defmodule BookApiWeb do
  @moduledoc """
  The entrypoint for defining your web interface, such
  as controllers, views, channels and so on.

  This can be used in your application as:

      use BookApiWeb, :controller
      use BookApiWeb, :view

  The definitions below will be executed for every view,
  controller, etc, so keep them short and clean, focused
  on imports, uses and aliases.

  Do NOT define functions inside the quoted expressions
  below. Instead, define any helper function in modules
  and import those modules here.
  """

  def controller do
    quote do
      use Phoenix.Controller, namespace: BookApiWeb

      import Plug.Conn
      import BookApiWeb.Gettext
      alias BookApiWeb.Router.Helpers, as: routes
    end
  end

  def view do
    quote do
      use Phoenix.View,
        root: "lib/book_api_web/templates",
        namespace: BookApiWeb

      # Import convenience functions from controllers
      import Phoenix.Controller,
        only: [get_csrf_token: 0, get_session: 2, put_session: 3, protect_from_forgery: 1]

      # Import basic rendering functionality
      import Phoenix.Renderer
      import BookApiWeb.Gettext
      alias BookApiWeb.Router.Helpers, as: routes
    end
  end

  def router do
    quote do
      use Phoenix.Router
      import Plug.Conn
      import Phoenix.Controller
    end
  end

  def channel do
    quote do
      use Phoenix.Channel
      import BookApiWeb.Gettext
    end
  end

  @doc """
  When used, dispatch to the appropriate controller/view/etc.
  """
  defmacro __using__(which) when is_atom(which) do
    apply(__MODULE__, which, [])
  end
end
