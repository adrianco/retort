defmodule BookApiWeb.Router do
  use Phoenix.Router

  pipeline :api do
    plug :accepts, ["json"]
    plug :put_format, "json"
  end

  scope "/api", BookApiWeb do
    pipe_through :api

    get "/health", HealthController, :index

    resources "/books", BookController, except: [:new, :edit]
  end
end
