defmodule BookApi.Web.Endpoint do
  use Phoenix.Endpoint, otp_app: :book_api

  # The session will be stored in the cookie and signed,
  # this means its contents can be read but not tampered with.
  # Set :encryption_salt if you would like to encrypt it.
  @session_options [
    store: :cookie,
    key: "_book_api_key",
    signing_salt: "ZQf+2V9f"
  ]

  plug Plug.Session, @session_options
  plug BookApi.Web.Router

  # Serve at "/" the static paths from the "priv/static" folder.
  plug Plug.Static,
    at: "/",
    from: :book_api,
    gzip: false,
    only: ~w(css fonts images js favicon.ico robots.txt)

  # Code reloading can be enabled on demand by setting :code_reloader to true.
  if Code.reloadable? do
    plug Phoenix.CodeReloader
  end

  plug Phoenix.Ecto.CheckRepoStatus
end
