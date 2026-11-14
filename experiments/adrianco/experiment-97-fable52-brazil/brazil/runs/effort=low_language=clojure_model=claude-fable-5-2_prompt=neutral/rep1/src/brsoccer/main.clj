(ns brsoccer.main
  "Entry point. `clojure -M:run` starts the MCP server on stdio;
  `clojure -M:run call <tool> '<json-args>'` runs one tool from the shell."
  (:require [brsoccer.data :as data]
            [brsoccer.mcp :as mcp]
            [brsoccer.tools :as tools]
            [clojure.data.json :as json])
  (:gen-class))

(defn -main [& [cmd tool args]]
  (case cmd
    "call" (let [{:keys [text error?]} (tools/call (data/db) tool (json/read-str (or args "{}")))]
             (.println (java.io.PrintStream. System/out true "UTF-8") ^String text)
             (System/exit (if error? 1 0)))
    "tools" (doseq [t tools/tools] (println (:name t) "-" (:description t)))
    (let [db (delay (data/db))]
      ;; Load in the background so the first tool call is fast but the
      ;; initialize handshake is answered immediately.
      (future (try @db (catch Throwable t (binding [*out* *err*] (println "Data load failed:" (ex-message t))))))
      (mcp/serve-stdio db)
      (shutdown-agents))))
