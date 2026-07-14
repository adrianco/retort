(ns brazilian-soccer-mcp.core
  (:require [cheshire.core :as json]
            [clojure.string :as str]
            [brazilian-soccer-mcp.data :as data]
            [brazilian-soccer-mcp.tools :as tools])
  (:gen-class))

(defn make-response [id result]
  {"jsonrpc" "2.0" "id" id "result" result})

(defn make-error [id code message]
  {"jsonrpc" "2.0" "id" id "error" {"code" code "message" message}})

(defn handle-message [msg]
  (let [method (get msg "method")
        id     (get msg "id")]
    (cond
      (= method "initialize")
      (make-response id
                     {"protocolVersion" "2024-11-05"
                      "capabilities"    {"tools" {}}
                      "serverInfo"      {"name" "brazilian-soccer-mcp" "version" "0.1.0"}})

      (nil? id)
      nil ; notifications have no id — no response needed

      (= method "tools/list")
      (make-response id {"tools" tools/tool-definitions})

      (= method "tools/call")
      (let [params    (get msg "params")
            tool-name (get params "name")
            arguments (get params "arguments" {})]
        (try
          (let [result (tools/call-tool tool-name arguments)]
            (make-response id {"content" [{"type" "text" "text" result}]
                               "isError" false}))
          (catch Exception e
            (make-response id {"content" [{"type" "text"
                                           "text" (str "Error: " (.getMessage e))}]
                               "isError" true}))))

      :else
      (make-error id -32601 (str "Method not found: " method)))))

(defn run-server []
  (data/load-all-data!)
  (let [reader (java.io.BufferedReader. *in*)]
    (loop []
      (when-let [line (try (.readLine reader) (catch Exception _ nil))]
        (let [trimmed (str/trim line)]
          (when (seq trimmed)
            (try
              (let [msg      (json/parse-string trimmed)
                    response (handle-message msg)]
                (when response
                  (println (json/generate-string response))
                  (flush)))
              (catch Exception e
                (println (json/generate-string
                           {"jsonrpc" "2.0"
                            "id"      nil
                            "error"   {"code"    -32700
                                       "message" (str "Parse error: " (.getMessage e))}}))
                (flush)))))
        (recur)))))

(defn -main [& _args]
  (run-server))
