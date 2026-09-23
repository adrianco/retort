defmodule BrSoccer.MCPServer do
  @moduledoc """
  Model Context Protocol server over stdio (newline-delimited JSON-RPC 2.0).

  Run with: `mix run --no-halt -e "BrSoccer.MCPServer.main()"` or `./run_mcp.sh`.
  """

  alias BrSoccer.{Data, Tools}

  @protocol "2024-11-05"

  def main do
    Data.load()
    loop()
  end

  defp loop do
    case IO.read(:stdio, :line) do
      :eof ->
        System.halt(0)

      {:error, _} ->
        System.halt(1)

      line ->
        case String.trim(line) do
          "" -> :ok
          json -> json |> handle_json() |> respond()
        end

        loop()
    end
  end

  defp respond(nil), do: :ok
  defp respond(resp), do: IO.write(JSON.encode!(resp) <> "\n")

  @doc "Handles one raw JSON-RPC message; returns a response map or nil for notifications."
  def handle_json(json) do
    case JSON.decode(json) do
      {:ok, msg} when is_map(msg) -> handle(msg)
      _ -> error(nil, -32700, "Parse error")
    end
  end

  def handle(%{"method" => method} = msg) do
    id = msg["id"]
    params = msg["params"] || %{}

    case {method, id} do
      {"notifications/" <> _, _} -> nil
      {_, nil} -> nil
      {"initialize", _} -> ok(id, initialize())
      {"ping", _} -> ok(id, %{})
      {"tools/list", _} -> ok(id, %{"tools" => Tools.definitions()})
      {"tools/call", _} -> ok(id, call_tool(params))
      _ -> error(id, -32601, "Method not found: #{method}")
    end
  end

  def handle(msg), do: error(msg["id"], -32600, "Invalid Request")

  defp initialize do
    %{
      "protocolVersion" => @protocol,
      "capabilities" => %{"tools" => %{}},
      "serverInfo" => %{"name" => "brazilian-soccer", "version" => "0.1.0"}
    }
  end

  defp call_tool(%{"name" => name} = params) do
    case Tools.call(name, params["arguments"] || %{}) do
      {:ok, text} -> %{"content" => [%{"type" => "text", "text" => text}], "isError" => false}
      {:error, text} -> %{"content" => [%{"type" => "text", "text" => text}], "isError" => true}
    end
  end

  defp call_tool(_), do: %{"content" => [%{"type" => "text", "text" => "Missing tool name"}], "isError" => true}

  defp ok(id, result), do: %{"jsonrpc" => "2.0", "id" => id, "result" => result}
  defp error(id, code, msg), do: %{"jsonrpc" => "2.0", "id" => id, "error" => %{"code" => code, "message" => msg}}
end
