defmodule BrazilianSoccerMcp.McpServer do
  @moduledoc """
  MCP protocol server communicating over stdio using JSON-RPC 2.0.
  Reads newline-delimited JSON from stdin and writes responses to stdout.
  """

  alias BrazilianSoccerMcp.Tools

  @server_info %{
    name: "brazilian-soccer-mcp",
    version: "1.0.0"
  }

  @capabilities %{
    tools: %{}
  }

  def run do
    loop()
  end

  defp loop do
    case IO.gets("") do
      :eof ->
        :ok

      {:error, _reason} ->
        :ok

      line when is_binary(line) ->
        line = String.trim(line)

        if line != "" do
          handle_line(line)
        end

        loop()
    end
  end

  defp handle_line(line) do
    case Jason.decode(line) do
      {:ok, request} ->
        response = handle_request(request)

        if response != nil do
          IO.puts(Jason.encode!(response))
        end

      {:error, reason} ->
        error_response = %{
          jsonrpc: "2.0",
          id: nil,
          error: %{code: -32700, message: "Parse error: #{inspect(reason)}"}
        }
        IO.puts(Jason.encode!(error_response))
    end
  end

  defp handle_request(%{"jsonrpc" => "2.0", "method" => method} = req) do
    id = Map.get(req, "id")
    params = Map.get(req, "params", %{})

    case method do
      "initialize" ->
        %{
          jsonrpc: "2.0",
          id: id,
          result: %{
            protocolVersion: "2024-11-05",
            capabilities: @capabilities,
            serverInfo: @server_info
          }
        }

      "notifications/initialized" ->
        # Notification - no response needed
        nil

      "tools/list" ->
        %{
          jsonrpc: "2.0",
          id: id,
          result: %{tools: Tools.list_tools()}
        }

      "tools/call" ->
        tool_name = get_in(params, ["name"])
        tool_params = Map.get(params, "arguments", %{})
        handle_tool_call(id, tool_name, tool_params)

      "ping" ->
        %{jsonrpc: "2.0", id: id, result: %{}}

      _ ->
        if id != nil do
          %{
            jsonrpc: "2.0",
            id: id,
            error: %{code: -32601, message: "Method not found: #{method}"}
          }
        else
          nil
        end
    end
  end

  defp handle_request(_invalid) do
    %{
      jsonrpc: "2.0",
      id: nil,
      error: %{code: -32600, message: "Invalid Request"}
    }
  end

  defp handle_tool_call(id, nil, _params) do
    %{
      jsonrpc: "2.0",
      id: id,
      error: %{code: -32602, message: "Missing tool name"}
    }
  end

  defp handle_tool_call(id, tool_name, params) do
    result = Tools.call_tool(tool_name, params)

    case result do
      {:error, msg} ->
        %{
          jsonrpc: "2.0",
          id: id,
          result: %{
            content: [%{type: "text", text: "Error: #{msg}"}],
            isError: true
          }
        }

      text when is_binary(text) ->
        %{
          jsonrpc: "2.0",
          id: id,
          result: %{
            content: [%{type: "text", text: text}],
            isError: false
          }
        }
    end
  rescue
    e ->
      %{
        jsonrpc: "2.0",
        id: id,
        result: %{
          content: [%{type: "text", text: "Internal error: #{Exception.message(e)}"}],
          isError: true
        }
      }
  end
end
