(ns brazilian-soccer-mcp.csv
  "Small RFC-4180-style CSV reader. It keeps this server self-contained apart from JSON.")

(defn parse-line [line]
  (loop [chars (seq (str line)), field "", row [], quoted? false]
    (if-let [c (first chars)]
      (cond
        (= c \") (if (and quoted? (= (second chars) \"))
                 (recur (nnext chars) (str field \" ) row quoted?)
                 (recur (next chars) field row (not quoted?)))
        (and (= c \,) (not quoted?)) (recur (next chars) "" (conj row field) false)
        :else (recur (next chars) (str field c) row quoted?))
      (conj row field))))

(defn read-csv [path]
  (let [[header & rows] (with-open [r (clojure.java.io/reader path :encoding "UTF-8")]
                        (doall (map parse-line (line-seq r))))
        keys (mapv #(keyword (clojure.string/replace % "^\\uFEFF" "")) header)]
    (mapv #(zipmap keys %) rows)))
