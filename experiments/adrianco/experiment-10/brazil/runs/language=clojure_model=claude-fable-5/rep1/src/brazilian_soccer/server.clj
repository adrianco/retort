(ns brazilian-soccer.server
  "CONTEXT
  =======
  MCP (Model Context Protocol) server for Brazilian soccer data, speaking
  JSON-RPC 2.0 over stdio (newline-delimited JSON), per
  https://modelcontextprotocol.io.

  Supported methods:
    initialize                ->  protocol handshake, advertises tools capability
    notifications/initialized ->  acknowledged silently (no response)
    notifications/cancelled   ->  ignored
    ping                      ->  {}
    tools/list                ->  the tool registry from brazilian-soccer.tools
    tools/call                ->  dispatch to a tool handler

  Conventions:
    * requests with an id get exactly one response; notifications get none
    * unknown method  -> error -32601, unknown tool/bad params -> -32602,
      parse errors -> -32700
    * tool handler exceptions are reported in-band as isError results
    * all diagnostics go to stderr; stdout carries only JSON-RPC frames

  Run with: clojure -M:run   (from the project root, so data/kaggle resolves;
  or set BRAZILIAN_SOCCER_DATA)."
  (:require [brazilian-soccer.data :as data]
            [brazilian-soccer.tools :as tools]
            [clojure.data.json :as json])
  (:gen-class))

(def server-info {:name "brazilian-soccer-mcp" :version "1.0.0"})

(def supported-protocol-versions
  #{"2024-11-05" "2025-03-26" "2025-06-18"})

(def default-protocol-version "2025-06-18")

(defn- result-response [id result]
  {:jsonrpc "2.0" :id id :result result})

(defn- error-response [id code message]
  {:jsonrpc "2.0" :id id :error {:code code :message message}})

(defn handle-initialize [{:keys [id params]}]
  (let [requested (:protocolVersion params)
        version (if (contains? supported-protocol-versions requested)
                  requested
                  default-protocol-version)]
    (result-response id {:protocolVersion version
                         :capabilities {:tools {:listChanged false}}
                         :serverInfo server-info
                         :instructions
                         (str "Answers questions about Brazilian soccer: "
                              "Brasileirão, Copa do Brasil and Copa Libertadores "
                              "matches (2003-2023), team records, standings, and "
                              "FIFA player data. Use tools/list to discover the "
                              "available query tools.")})))

(defn handle-tools-list [{:keys [id]}]
  (result-response id {:tools (tools/list-tools)}))

(defn handle-tools-call [{:keys [id params]}]
  (let [{:keys [name arguments]} params]
    (if-let [result (tools/call-tool name arguments)]
      (result-response id result)
      (error-response id -32602 (str "Unknown tool: " name)))))

(defn handle-message
  "Handle one parsed JSON-RPC message.  Returns a response map, or nil for
  notifications (which must not be answered)."
  [{:keys [id method] :as msg}]
  (cond
    (= method "initialize")                (handle-initialize msg)
    (= method "notifications/initialized") nil
    (= method "notifications/cancelled")   nil
    (= method "ping")                      (result-response id {})
    (= method "tools/list")                (handle-tools-list msg)
    (= method "tools/call")                (handle-tools-call msg)
    ;; ignore unknown notifications, reject unknown requests
    (nil? id)                              nil
    :else (error-response id -32601 (str "Method not found: " method))))

(defn handle-line
  "Parse one line of input and produce a response JSON string, or nil."
  [line]
  (let [msg (try (json/read-str line :key-fn keyword)
                 (catch Exception _ ::parse-error))]
    (cond
      (= msg ::parse-error)
      (json/write-str (error-response nil -32700 "Parse error"))

      (map? msg)
      (some-> (try (handle-message msg)
                   (catch Exception e
                     (error-response (:id msg) -32603
                                     (str "Internal error: " (.getMessage e)))))
              json/write-str)

      :else
      (json/write-str (error-response nil -32600 "Invalid request")))))

(defn -main [& _]
  (binding [*err* (java.io.PrintWriter. System/err true)]
    (.println ^java.io.PrintWriter *err* "[brazilian-soccer-mcp] loading data...")
    (let [db (data/db)]
      (.println ^java.io.PrintWriter *err*
                (str "[brazilian-soccer-mcp] ready: "
                     (count (:matches db)) " matches, "
                     (count (:players db)) " players")))
    (let [out (java.io.PrintWriter.
               (java.io.OutputStreamWriter. System/out java.nio.charset.StandardCharsets/UTF_8)
               true)
          in (java.io.BufferedReader.
              (java.io.InputStreamReader. System/in java.nio.charset.StandardCharsets/UTF_8))]
      (loop []
        (when-let [line (.readLine in)]
          (when-not (.isEmpty (.trim line))
            (when-let [response (handle-line line)]
              (.println out response)))
          (recur)))))
  (System/exit 0))
