(ns brazilian-soccer.json-test
  (:require [brazilian-soccer.json :as json]
            [clojure.test :refer [deftest is testing]]))

(deftest decodes-json-rpc-shapes
  (is (= {"jsonrpc" "2.0" "id" 1 "method" "ping"
          "params" {"a" [1 2.5 true false nil]}}
         (json/decode "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"ping\",\"params\":{\"a\":[1,2.5,true,false,null]}}"))))

(deftest decodes-string-escapes
  (is (= "a\"b\\c\nd\t/" (json/decode "\"a\\\"b\\\\c\\nd\\t\\/\"")))
  (is (= "é" (json/decode "\"\\u00e9\""))))

(deftest encodes-maps-with-keyword-or-string-keys
  (is (= "{\"id\":1,\"result\":{\"ok\":true,\"items\":[]}}"
         (json/encode {:id 1 :result {"ok" true :items []}}))))

(deftest encodes-escapes-and-unicode
  (is (= "\"a\\\"b\\n\\tSão\"" (json/encode "a\"b\n\tSão")))
  (is (= "null" (json/encode nil)))
  (is (= "2.5" (json/encode 5/2))))

(deftest round-trips-unicode-text
  (let [s "Grêmio — Avaí"]
    (is (= s (json/decode (json/encode s))))))

(deftest rejects-malformed-input
  (is (thrown? Exception (json/decode "{\"a\":")))
  (is (thrown? Exception (json/decode "{} trailing"))))
