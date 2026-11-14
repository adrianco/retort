defmodule BrazilianSoccer.MCP.Server do
  @moduledoc """
  Model Context Protocol server over stdio (newline-delimited JSON-RPC 2.0).

  Implements `initialize`, `ping`, `tools/list` and `tools/call`.
  `handle/1` is pure (decoded request map in, response map or nil out) so the
  protocol can be tested without a transport.
  """

  alias BrazilianSoccer.Tools

  @protocol_versions ["2025-06-18", "2025-03-26", "2024-11-05"]
  @server_info %{
    "name" => "brazilian-soccer",
    "title" => "Brazilian Soccer Knowledge Base",
    "version" => "0.1.0"
  }

  @doc "Reads requests from `input` until EOF, writing responses to `output`."
  def run(input \\ :stdio, output \\ :stdio) do
    case IO.read(input, :line) do
      :eof ->
        :ok

      {:error, _} ->
        :ok

      line ->
        case handle_line(line) do
          nil -> :ok
          json -> IO.write(output, [json, "\n"])
        end

        run(input, output)
    end
  end

  @doc "Handles one line of input; returns the JSON response string or nil."
  def handle_line(line) do
    case String.trim(line) do
      "" ->
        nil

      text ->
        case JSON.decode(text) do
          {:ok, batch} when is_list(batch) and batch != [] ->
            case batch |> Enum.map(&handle/1) |> Enum.reject(&is_nil/1) do
              [] -> nil
              responses -> JSON.encode!(responses)
            end

          {:ok, msg} when is_map(msg) ->
            case handle(msg) do
              nil -> nil
              response -> JSON.encode!(response)
            end

          {:ok, _} ->
            JSON.encode!(error(nil, -32600, "Invalid Request"))

          {:error, _} ->
            JSON.encode!(error(nil, -32700, "Parse error"))
        end
    end
  end

  @doc "Handles a decoded JSON-RPC message. Notifications return nil."
  def handle(%{"method" => method} = msg) when is_binary(method) do
    id = Map.get(msg, "id")
    params = Map.get(msg, "params") || %{}

    cond do
      not Map.has_key?(msg, "id") -> nil
      true -> request(method, params, id)
    end
  end

  # responses from the client (we never send requests) are ignored
  def handle(%{"id" => _} = msg) when is_map_key(msg, "result") or is_map_key(msg, "error"),
    do: nil

  def handle(msg) when is_map(msg), do: error(Map.get(msg, "id"), -32600, "Invalid Request")
  def handle(_), do: error(nil, -32600, "Invalid Request")

  defp request("initialize", params, id) do
    requested = params["protocolVersion"]
    version = if requested in @protocol_versions, do: requested, else: hd(@protocol_versions)

    result(id, %{
      "protocolVersion" => version,
      "capabilities" => %{"tools" => %{"listChanged" => false}},
      "serverInfo" => @server_info,
      "instructions" =>
        "Knowledge base of Brazilian soccer: Brasileirão (Série A/B/C), Copa do Brasil and Copa Libertadores matches " <>
          "plus the FIFA player database. Team names are normalised, so any common spelling works. " <>
          "Start with dataset_info to see coverage."
    })
  end

  defp request("ping", _params, id), do: result(id, %{})
  defp request("tools/list", _params, id), do: result(id, %{"tools" => Tools.list()})

  defp request("tools/call", params, id) do
    name = params["name"]
    args = params["arguments"] || %{}

    cond do
      not is_binary(name) ->
        error(id, -32602, "Missing tool name")

      not is_map(args) ->
        error(id, -32602, "Tool arguments must be an object")

      true ->
        case Tools.call(name, args) do
          {:ok, text} ->
            result(id, %{"content" => [%{"type" => "text", "text" => text}], "isError" => false})

          {:error, :unknown_tool} ->
            error(id, -32602, "Unknown tool: #{name}")

          {:error, text} ->
            result(id, %{"content" => [%{"type" => "text", "text" => text}], "isError" => true})
        end
    end
  end

  defp request(method, _params, id), do: error(id, -32601, "Method not found: #{method}")

  defp result(id, result), do: %{"jsonrpc" => "2.0", "id" => id, "result" => result}

  defp error(id, code, message),
    do: %{"jsonrpc" => "2.0", "id" => id, "error" => %{"code" => code, "message" => message}}
end
