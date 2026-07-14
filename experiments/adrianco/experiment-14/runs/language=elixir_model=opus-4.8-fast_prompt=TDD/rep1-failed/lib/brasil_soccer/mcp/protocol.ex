defmodule BrasilSoccer.MCP.Protocol do
  @moduledoc """
  Pure JSON-RPC 2.0 dispatch for the Model Context Protocol.

  `handle/2` takes a decoded request map and the in-memory dataset and returns a
  response map to encode and send back, or `nil` for notifications (which must
  not be answered). Keeping this pure makes the protocol behaviour fully
  unit-testable without any IO.
  """

  alias BrasilSoccer.MCP.Tools

  @protocol_version "2024-11-05"
  @server_name "brazil-soccer-mcp"
  @server_version "0.1.0"

  @doc "Handle a single decoded JSON-RPC request against `data`."
  @spec handle(map(), Tools.data()) :: map() | nil
  def handle(%{"method" => method} = req, data) do
    id = req["id"]
    params = req["params"] || %{}

    cond do
      notification?(method) -> nil
      true -> dispatch(method, params, id, data)
    end
  end

  defp notification?("notifications/" <> _), do: true
  defp notification?(_), do: false

  defp dispatch("initialize", _params, id, _data) do
    result(id, %{
      "protocolVersion" => @protocol_version,
      "capabilities" => %{"tools" => %{"listChanged" => false}},
      "serverInfo" => %{"name" => @server_name, "version" => @server_version}
    })
  end

  defp dispatch("ping", _params, id, _data), do: result(id, %{})

  defp dispatch("tools/list", _params, id, _data) do
    result(id, %{"tools" => Tools.specs()})
  end

  defp dispatch("tools/call", params, id, data) do
    name = params["name"]
    args = params["arguments"] || %{}

    case Tools.call(name, args, data) do
      {:ok, text} -> result(id, tool_content(text, false))
      {:error, message} -> result(id, tool_content(message, true))
    end
  end

  defp dispatch(method, _params, id, _data) do
    error(id, -32601, "Method not found: #{method}")
  end

  defp tool_content(text, is_error?) do
    %{"content" => [%{"type" => "text", "text" => text}], "isError" => is_error?}
  end

  defp result(id, result) do
    %{"jsonrpc" => "2.0", "id" => id, "result" => result}
  end

  defp error(id, code, message) do
    %{"jsonrpc" => "2.0", "id" => id, "error" => %{"code" => code, "message" => message}}
  end
end
