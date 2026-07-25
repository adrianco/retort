(ns brazilian-soccer.mcp
  "Model Context Protocol server: JSON-RPC 2.0 over newline delimited stdio.

  CONTEXT
  -------
  MCP clients (Claude Desktop, the MCP inspector, any LLM host) launch this
  process and speak JSON-RPC on its stdin/stdout, one JSON object per line.
  The handshake and the methods implemented here are:

      initialize                -> protocol version, capabilities, server info
      notifications/initialized -> acknowledged silently (no response)
      ping                      -> {}
      tools/list                -> the catalogue from brazilian-soccer.tools
      tools/call                -> {content:[{type:\"text\",...}], isError}

  Anything else gets a JSON-RPC -32601.  Tool failures are *not* JSON-RPC
  errors: MCP wants them reported as a result with isError true so the model
  can read the message and retry, which is how \"did you mean Atlético Mineiro
  or Athletico Paranaense?\" reaches the user.

  `handle-message` is a pure function of [db message] so the protocol can be
  tested without spawning a process; `serve` is the thin I/O loop."
  (:require [clojure.data.json :as json]
            [clojure.string :as str]
            [brazilian-soccer.tools :as tools]))

(def protocol-version "2024-11-05")
(def supported-protocol-versions #{"2024-11-05" "2025-03-26" "2025-06-18"})

(def server-info {"name" "brazilian-soccer" "version" "1.0.0"})

(def instructions
  (str "Knowledge graph of Brazilian football built from six Kaggle datasets: "
       "16,000+ matches (Brasileirão Série A/B/C 2003-2023, Copa do Brasil 2012-2023, "
       "Copa Libertadores 2013-2022) and the FIFA 19 player database. "
       "Call dataset_info first if you are unsure what is covered. Club names may be "
       "written in any spelling found in the data (\"Flamengo\", \"Flamengo-RJ\", "
       "\"Atletico Mineiro\", \"Atlético - MG\"). Standings and averages are calculated "
       "from the match results present in the data, not copied from an official table."))

(defn- ok [id result] {"jsonrpc" "2.0" "id" id "result" result})

(defn- rpc-error [id code message]
  {"jsonrpc" "2.0" "id" id "error" {"code" code "message" message}})

(defn- text-result [text error?]
  {"content" [{"type" "text" "text" text}] "isError" (boolean error?)})

(defn- initialize-result [params]
  (let [requested (get params "protocolVersion")]
    {"protocolVersion" (if (supported-protocol-versions requested) requested protocol-version)
     "capabilities" {"tools" {"listChanged" false}}
     "serverInfo" server-info
     "instructions" instructions}))

(defn handle-message
  "Handle one decoded JSON-RPC message.  Returns the response map, or nil for
  notifications (messages without an id), which must not be answered."
  [db message]
  (let [{:strs [id method params]} message
        notification? (not (contains? message "id"))]
    (cond
      (nil? method)
      (when-not notification? (rpc-error id -32600 "Invalid request: no method"))

      (= method "initialize") (ok id (initialize-result params))
      (= method "ping")       (ok id {})

      (str/starts-with? method "notifications/") nil

      (= method "tools/list")
      (ok id {"tools" (tools/tool-list-json)})

      (= method "tools/call")
      (let [tool-name (get params "name")
            args      (or (get params "arguments") {})]
        (try
          (ok id (text-result (tools/call-tool db tool-name args) false))
          (catch Exception e
            (ok id (text-result (str "Tool " tool-name " failed: "
                                     (or (.getMessage e) (str e)))
                                true)))))

      :else
      (when-not notification?
        (rpc-error id -32601 (str "Method not found: " method))))))

(defn handle-line
  "Decode a line, dispatch it and encode the response (nil when silent)."
  [db line]
  (let [message (try (json/read-str line)
                     (catch Exception e
                       {::parse-error (.getMessage e)}))]
    (cond
      (::parse-error message)
      (json/write-str (rpc-error nil -32700 (str "Parse error: " (::parse-error message))))

      (not (map? message))
      (json/write-str (rpc-error nil -32600 "Invalid request: expected a JSON object"))

      :else
      (some-> (handle-message db message) json/write-str))))

(defn serve
  "Read newline delimited JSON-RPC from `in`, write responses to `out`.
  Both streams are forced to UTF-8: club names carry accents and cedillas and
  the platform default encoding cannot be trusted."
  [db in out]
  (let [reader (java.io.BufferedReader. (java.io.InputStreamReader. in "UTF-8"))
        writer (java.io.PrintWriter. (java.io.OutputStreamWriter. out "UTF-8") true)]
    (doseq [line (line-seq reader)
            :when (not (str/blank? line))]
      (when-let [response (handle-line db line)]
        (.println writer response)
        (.flush writer)))))
