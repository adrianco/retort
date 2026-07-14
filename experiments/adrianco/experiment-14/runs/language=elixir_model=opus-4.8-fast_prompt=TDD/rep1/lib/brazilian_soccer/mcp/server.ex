defmodule BrazilianSoccer.MCP.Server do
  @moduledoc """
  JSON-RPC 2.0 request handling for the Model Context Protocol.

  `handle/2` is a pure function: it takes a decoded JSON-RPC request map and a
  `Dataset`, and returns the response map to encode and send back (or `nil` for
  notifications, which receive no response). The transport (stdio framing) lives
  in `BrazilianSoccer.MCP.CLI`.
  """

  alias BrazilianSoccer.Dataset
  alias BrazilianSoccer.MCP.Tools

  @protocol_version "2024-11-05"
  @server_name "brazilian-soccer-mcp"
  @server_version "0.1.0"

  # JSON-RPC error codes
  @method_not_found -32_601
  @invalid_request -32_600

  @doc """
  Handle a single decoded JSON-RPC request. Returns the response map, or `nil`
  for notifications (requests without an `id`).
  """
  @spec handle(map(), Dataset.t()) :: map() | nil
  def handle(%{"method" => method} = request, %Dataset{} = dataset) do
    id = Map.get(request, "id")
    params = Map.get(request, "params", %{}) || %{}

    case dispatch(method, params, dataset) do
      {:result, result} -> result_response(id, result)
      {:error, code, message} -> error_response(id, code, message)
      :notification -> nil
    end
  end

  def handle(_invalid, %Dataset{}) do
    error_response(nil, @invalid_request, "Invalid Request")
  end

  defp dispatch("initialize", _params, _ds) do
    {:result,
     %{
       "protocolVersion" => @protocol_version,
       "capabilities" => %{"tools" => %{}},
       "serverInfo" => %{"name" => @server_name, "version" => @server_version}
     }}
  end

  defp dispatch("tools/list", _params, _ds) do
    tools = Enum.map(Tools.list(), &tool_spec/1)
    {:result, %{"tools" => tools}}
  end

  defp dispatch("tools/call", params, ds) do
    name = params["name"]
    arguments = params["arguments"] || %{}

    case Tools.call(name, arguments, ds) do
      {:ok, text} -> {:result, content(text, false)}
      {:error, message} -> {:result, content(message, true)}
    end
  end

  defp dispatch("ping", _params, _ds), do: {:result, %{}}

  defp dispatch("notifications/" <> _, _params, _ds), do: :notification

  defp dispatch(method, _params, _ds) do
    {:error, @method_not_found, "Method not found: #{method}"}
  end

  defp tool_spec(tool) do
    %{
      "name" => tool.name,
      "description" => tool.description,
      "inputSchema" => tool.input_schema
    }
  end

  defp content(text, is_error?) do
    %{
      "content" => [%{"type" => "text", "text" => text}],
      "isError" => is_error?
    }
  end

  # A request without an id is a notification: no response is sent.
  defp result_response(nil, _result), do: nil

  defp result_response(id, result) do
    %{"jsonrpc" => "2.0", "id" => id, "result" => result}
  end

  defp error_response(id, code, message) do
    %{
      "jsonrpc" => "2.0",
      "id" => id,
      "error" => %{"code" => code, "message" => message}
    }
  end
end
