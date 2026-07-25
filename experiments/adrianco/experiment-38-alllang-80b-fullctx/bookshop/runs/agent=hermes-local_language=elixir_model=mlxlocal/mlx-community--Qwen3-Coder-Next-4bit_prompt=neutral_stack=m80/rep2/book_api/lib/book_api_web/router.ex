defmodule BookApiWeb.Router do
  use Phoenix.Router

  pipeline :api do
    plug :accepts, ["json"]
  end

  scope "/api" do
    pipe_through :api

    # Health check endpoint
    get "/health", HealthController, :health

    # Books resources
    resources "/books", BookController, except: [:new, :edit]
  end
end
