(ns brazilian-soccer-mcp.dates
  (:require [clojure.string :as str])
  (:import [java.time LocalDate]
           [java.time.format DateTimeFormatter DateTimeParseException]))

(def formatters
  [(DateTimeFormatter/ofPattern "yyyy-MM-dd HH:mm:ss")
   (DateTimeFormatter/ofPattern "yyyy-MM-dd")
   (DateTimeFormatter/ofPattern "dd/MM/yyyy")])

(defn parse-date
  "Parses a date string in various formats. Returns a LocalDate or nil."
  [date-str]
  (when (and date-str (not (str/blank? date-str)))
    (some (fn [fmt]
            (try
              (let [parsed (java.time.LocalDateTime/parse date-str fmt)]
                (.toLocalDate parsed))
              (catch DateTimeParseException _
                (try
                  (LocalDate/parse date-str fmt)
                  (catch DateTimeParseException _ nil)))))
          formatters)))

(defn year [d] (when d (.getYear d)))
(defn month [d] (when d (.getMonthValue d)))
(defn day [d] (when d (.getDayOfMonth d)))

(defn date-in-range?
  "Returns true if date falls within [from, to] (inclusive). nil bounds mean no constraint."
  [d from-str to-str]
  (when d
    (let [from (when from-str (parse-date from-str))
          to   (when to-str   (parse-date to-str))]
      (and (or (nil? from) (not (.isBefore d from)))
           (or (nil? to)   (not (.isAfter d to)))))))

(defn extract-year
  "Extracts the year as an integer from a date string, or nil."
  [date-str]
  (when-let [d (parse-date date-str)]
    (year d)))
