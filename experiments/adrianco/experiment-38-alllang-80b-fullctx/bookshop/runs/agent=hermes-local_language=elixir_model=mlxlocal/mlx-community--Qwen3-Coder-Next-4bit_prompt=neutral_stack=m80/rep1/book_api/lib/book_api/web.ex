defmodule BookApi.Web do
  @moduledoc """
  The entrypoint for defining your web interface, such
  as controllers, views, channels and so on.

  This can be used in your application as:

      use BookApi.Web, :controller
      use BookApi.Web, :view

  The definitions below will be executed for every view,
  controller, etc, so keep them short and clean, focused
  on imports, uses and aliases.

  Do NOT define functions inside the quoted expressions
  below. Instead, define any helper function in modules
  and import those modules here.
  """

  def controller do
    quote do
      use Phoenix.Controller, namespace: BookApi.Web, formats: [:json]

      import Plug.Conn
      unquote(verified_routes())
    end
  end

  def view do
    quote do
      use Phoenix.View,
        root: "lib/book_api/web/templates",
        namespace: BookApi.Web

      # Import convenience functions from controllers
      import Phoenix.Controller,
        only: [get_csrf_token: 0, get_flash: 1, get_flash: 2, view_module: 1]

      # Use all HTML functionality (forms, tags, etc)
      use Phoenix.HTML

      unquote(verified_routes())
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
    end
  end

  def verified_routes do
    quote do
      use Phoenix.VerifiedRoutes,
        endpoint: BookApi.Web.Endpoint,
        router: BookApi.Web.Router,
        static: "priv/static"
    end
  end

  @doc """
  Use this definition to include helpers in your controllers and views.
  """
  def helpers do
    quote do
      import Phoenix.HTML
      import Phoenix.HTML.Form
      import Phoenix.HTML.Link
      import Phoenix.HTML.Tag
    end
  end

  defmacro __using__(which) when is_atom(which) do
    apply(__MODULE__, which, [])
  end
end
