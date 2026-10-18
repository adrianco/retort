(ns brazil-soccer.mcp
  "Minimal Model Context Protocol server over stdio: newline-delimited JSON-RPC 2.0
  with the tools capability only."
  (:require [cheshire.core :as json]
            [clojure.java.io :as io]
            [clojure.string :as str]))

(def protocol-version "2024-11-05")

(def server-info {:name "brazilian-soccer-mcp" :version "0.1.0"})

(defn- ok [id result] {:jsonrpc "2.0" :id id :result result})

(defn- failure [id code message]
  {:jsonrpc "2.0" :id id :error {:code code :message message}})

(defn- tool-result [text error?]
  {:content [{:type "text" :text text}] :isError error?})

(defn- call-tool
  "Runs a tool and wraps its output; failures are reported as tool errors, not
  protocol errors, so the model can see the message and retry."
  [{:keys [handler]} arguments]
  (try
    (tool-result (handler (or arguments {})) false)
    (catch Exception e
      (tool-result (or (ex-message e) (str e)) true))))

(defn handle-message
  "Response map for one parsed JSON-RPC message, or nil for notifications."
  [{:keys [id method params]} tools]
  (when (some? id)
    (case method
      "initialize" (ok id {:protocolVersion protocol-version
                           :capabilities {:tools {}}
                           :serverInfo server-info})
      "ping" (ok id {})
      "tools/list" (ok id {:tools (mapv #(select-keys % [:name :description :inputSchema]) tools)})
      "tools/call" (let [tool (first (filter #(= (:name %) (:name params)) tools))]
                     (if tool
                       (ok id (call-tool tool (:arguments params)))
                       (failure id -32602 (str "Unknown tool: " (:name params)))))
      (failure id -32601 (str "Method not found: " method)))))

(defn serve
  "Reads JSON-RPC messages from `in` and writes responses to `out` until EOF."
  [in out tools]
  (let [writer (io/writer out)
        send! (fn [resp]
                (.write writer (json/generate-string resp))
                (.write writer "\n")
                (.flush writer))]
    (doseq [line (line-seq (io/reader in))
            :when (not (str/blank? line))]
      (let [msg (try (json/parse-string line true)
                     (catch Exception _ ::parse-error))]
        (if (= msg ::parse-error)
          (send! (failure nil -32700 "Parse error"))
          (when-let [resp (handle-message msg tools)]
            (send! resp)))))))
