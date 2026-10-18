(ns brazilian-soccer.json
  "Small JSON encoder and decoder for MCP JSON-RPC messages.
  Decoding produces maps with string keys; encoding accepts keyword or string keys."
  (:require [clojure.string :as str]))

(defn- escape-string [^String s]
  (let [sb (StringBuilder. "\"")]
    (doseq [c s]
      (case c
        \" (.append sb "\\\"")
        \\ (.append sb "\\\\")
        \newline (.append sb "\\n")
        \return (.append sb "\\r")
        \tab (.append sb "\\t")
        (if (< (int c) 0x20)
          (.append sb (format "\\u%04x" (int c)))
          (.append sb c))))
    (.append sb \")
    (str sb)))

(defn encode
  "Serializes Clojure data to a JSON string."
  [x]
  (cond
    (nil? x) "null"
    (true? x) "true"
    (false? x) "false"
    (string? x) (escape-string x)
    (keyword? x) (escape-string (name x))
    (ratio? x) (str (double x))
    (number? x) (str x)
    (map? x) (str "{"
                  (str/join
                   ","
                   (map (fn [[k v]]
                          (str (escape-string (if (keyword? k) (name k) (str k)))
                               ":" (encode v)))
                        x))
                  "}")
    (sequential? x) (str "[" (str/join "," (map encode x)) "]")
    (set? x) (encode (vec x))
    :else (escape-string (str x))))

(defn- ws [^String s i]
  (loop [i i]
    (if (and (< i (count s)) (Character/isWhitespace (.charAt s i)))
      (recur (inc i))
      i)))

(def ^:private simple-escapes
  {\n \newline, \t \tab, \r \return, \b \backspace, \f \formfeed, \" \", \\ \\, \/ \/})

(defn- parse-string
  "Parses a string body starting just after the opening quote.
  Returns [string index-after-closing-quote]."
  [^String s start]
  (let [sb (StringBuilder.)]
    (loop [i start]
      (let [c (.charAt s i)]
        (cond
          (= c \") [(str sb) (inc i)]

          (= c \\)
          (let [e (.charAt s (inc i))]
            (if (= e \u)
              (do (.append sb (char (Integer/parseInt (subs s (+ i 2) (+ i 6)) 16)))
                  (recur (+ i 6)))
              (do (.append sb (get simple-escapes e e))
                  (recur (+ i 2)))))

          :else (do (.append sb c) (recur (inc i))))))))

(declare parse-value)

(defn- parse-object [^String s i]
  (loop [i (ws s (inc i)), m {}]
    (if (= \} (.charAt s i))
      [m (inc i)]
      (let [[k i] (parse-value s i)
            i (ws s i)
            _ (when-not (= \: (.charAt s i)) (throw (ex-info "Expected ':'" {:at i})))
            [v i] (parse-value s (inc i))
            i (ws s i)
            m (assoc m k v)]
        (if (= \, (.charAt s i))
          (recur (ws s (inc i)) m)
          (do (when-not (= \} (.charAt s i)) (throw (ex-info "Expected '}'" {:at i})))
              [m (inc i)]))))))

(defn- parse-array [^String s i]
  (loop [i (ws s (inc i)), v []]
    (if (= \] (.charAt s i))
      [v (inc i)]
      (let [[x i] (parse-value s i)
            i (ws s i)
            v (conj v x)]
        (if (= \, (.charAt s i))
          (recur (ws s (inc i)) v)
          (do (when-not (= \] (.charAt s i)) (throw (ex-info "Expected ']'" {:at i})))
              [v (inc i)]))))))

(defn- parse-value [^String s i]
  (let [i (ws s i)
        c (.charAt s i)]
    (cond
      (= c \{) (parse-object s i)
      (= c \[) (parse-array s i)
      (= c \") (parse-string s (inc i))
      (.startsWith s "true" i) [true (+ i 4)]
      (.startsWith s "false" i) [false (+ i 5)]
      (.startsWith s "null" i) [nil (+ i 4)]
      :else
      (if-let [lexeme (re-find #"^-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?" (subs s i))]
        (let [n (if (re-find #"[.eE]" lexeme)
                  (Double/parseDouble lexeme)
                  (Long/parseLong lexeme))]
          [n (+ i (count lexeme))])
        (throw (ex-info "Unexpected JSON token" {:at i}))))))

(defn decode
  "Parses a JSON string. Throws ex-info on malformed input."
  [^String s]
  (let [[v i] (parse-value s 0)]
    (when-not (= (ws s i) (count s))
      (throw (ex-info "Trailing characters after JSON value" {:at i})))
    v))
