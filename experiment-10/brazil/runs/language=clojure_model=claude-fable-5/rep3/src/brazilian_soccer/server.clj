(ns brazilian-soccer.server
  "MCP (Model Context Protocol) server over stdio.
  Speaks newline-delimited JSON-RPC 2.0: initialize, tools/list, tools/call."
  (:gen-class)
  (:require [brazilian-soccer.data :as data]
            [brazilian-soccer.tools :as tools]
            [clojure.data.json :as json]
            [clojure.string :as str]))

(def protocol-version "2024-11-05")
(def server-info {:name "brazilian-soccer-mcp" :version "1.0.0"})

(defn- result-response [id result]
  {:jsonrpc "2.0" :id id :result result})

(defn- error-response [id code message]
  {:jsonrpc "2.0" :id id :error {:code code :message message}})

(defn handle-request
  "Handles one parsed JSON-RPC message (string keys). Returns the response
  map, or nil for notifications (which must not be answered)."
  [db req]
  (let [id     (get req "id")
        method (get req "method")
        params (get req "params")]
    (cond
      ;; Notifications never get a response.
      (and (some? method) (nil? id))
      nil

      (= method "initialize")
      (result-response id {:protocolVersion (or (get params "protocolVersion") protocol-version)
                           :capabilities    {:tools {:listChanged false}}
                           :serverInfo      server-info})

      (= method "ping")
      (result-response id {})

      (= method "tools/list")
      (result-response id {:tools (tools/list-tools)})

      (= method "tools/call")
      (result-response id (tools/call-tool db
                                           (get params "name")
                                           (get params "arguments")))

      :else
      (error-response id -32601 (str "Method not found: " method)))))

(defn handle-line
  "Parses one line of input and produces the JSON response string, or nil."
  [db line]
  (when-not (str/blank? line)
    (let [req (try (json/read-str line)
                   (catch Exception _ ::parse-error))]
      (some-> (if (= req ::parse-error)
                (error-response nil -32700 "Parse error")
                (handle-request db req))
              (json/write-str :escape-unicode false)))))

(defn run
  "Reads JSON-RPC messages line-by-line from `in`, writes responses to `out`."
  [db in out]
  (doseq [line (line-seq in)]
    (when-let [response (handle-line db line)]
      (.write ^java.io.Writer out (str response "\n"))
      (.flush ^java.io.Writer out))))

(defn -main [& args]
  (let [dir (or (first args) data/*data-dir*)
        db  (binding [data/*data-dir* dir] @data/db)]
    (binding [*err* (java.io.PrintWriter. System/err true)]
      (.println ^java.io.PrintWriter *err*
                (format "brazilian-soccer-mcp ready: %d matches, %d extended rows, %d players"
                        (count (:matches db)) (count (:extended db)) (count (:players db)))))
    (run db
         (java.io.BufferedReader. (java.io.InputStreamReader. System/in "UTF-8"))
         (java.io.BufferedWriter. (java.io.OutputStreamWriter. System/out "UTF-8")))))
