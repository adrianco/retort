defmodule BookApi.ConnCase do
  use ExUnit.CaseTemplate

  using do
    quote do
      import Plug.Test
      import Plug.Conn
      alias BookApi.Repo

      @router_opts BookApi.Router.init([])

      defp call(method, path, body \\ nil) do
        conn =
          case body do
            nil ->
              conn(method, path)

            body when is_binary(body) ->
              conn(method, path, body)
              |> put_req_header("content-type", "application/json")

            body ->
              conn(method, path, Jason.encode!(body))
              |> put_req_header("content-type", "application/json")
          end

        BookApi.Router.call(conn, @router_opts)
      end

      defp json_body(conn), do: Jason.decode!(conn.resp_body)
    end
  end

  setup tags do
    pid = Ecto.Adapters.SQL.Sandbox.start_owner!(BookApi.Repo, shared: not tags[:async])
    on_exit(fn -> Ecto.Adapters.SQL.Sandbox.stop_owner(pid) end)
    :ok
  end
end
