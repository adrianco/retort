defmodule BookApi.Web.Router do
  use BookApi.Web, :router

  pipeline :api do
    plug :accepts, ["json"]
  end

  scope "/api" do
    pipe_through :api

    # Health check endpoint
    get "/health", HealthController, :index

    # Books resources
    resources "/books", BookController, except: [:new, :edit]
  end
end
