(ns brazilian-soccer.csv
  "Minimal RFC 4180 CSV reader: quoted fields, doubled quotes, embedded
  commas/newlines, CRLF line endings and a leading UTF-8 BOM."
  (:require [clojure.string :as str]))

(defn- strip-bom [^String s]
  (if (and (seq s) (= (char 0xfeff) (first s))) (subs s 1) s))

(defn parse-rows
  "Parses CSV text into a vector of rows, each a vector of strings.
  Blank lines are skipped."
  [text]
  (let [text (strip-bom text)
        n (count text)
        sb (StringBuilder.)
        end-field (fn [row]
                    (let [s (str sb)]
                      (.setLength sb 0)
                      (conj row s)))]
    (loop [i 0, in-quotes? false, row [], rows []]
      (if (>= i n)
        (let [rows (if (or (seq row) (pos? (.length sb)))
                     (conj rows (end-field row))
                     rows)]
          (vec (remove #(= [""] %) rows)))
        (let [c (.charAt text i)]
          (cond
            in-quotes?
            (cond
              (and (= c \") (< (inc i) n) (= \" (.charAt text (inc i))))
              (do (.append sb \") (recur (+ i 2) true row rows))

              (= c \")
              (recur (inc i) false row rows)

              :else
              (do (.append sb c) (recur (inc i) true row rows)))

            (= c \")  (recur (inc i) true row rows)
            (= c \,)  (recur (inc i) false (end-field row) rows)
            (= c \return) (recur (inc i) false row rows)
            (= c \newline) (recur (inc i) false [] (conj rows (end-field row)))
            :else (do (.append sb c) (recur (inc i) false row rows))))))))

(defn read-maps
  "Reads a CSV file and returns a vector of maps keyed by trimmed header names."
  [path]
  (let [[header & body] (parse-rows (slurp path :encoding "UTF-8"))
        ks (mapv str/trim header)]
    (mapv #(zipmap ks %) body)))
