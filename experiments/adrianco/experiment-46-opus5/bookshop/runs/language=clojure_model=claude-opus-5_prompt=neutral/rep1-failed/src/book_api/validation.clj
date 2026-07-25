(ns book-api.validation
  "Request-body validation and coercion for book payloads."
  (:require [clojure.string :as str]))

(def ^:private max-title-length 500)
(def ^:private max-author-length 500)
(def ^:private min-year 1)
(def ^:private max-year 2200)

(defn- blank-string? [v]
  (and (string? v) (str/blank? v)))

(defn- trimmed [v]
  (when (string? v) (str/trim v)))

(defn- check-required-text [errors field v max-length]
  (cond
    (nil? v)          (conj errors {:field field :message "is required"})
    (not (string? v)) (conj errors {:field field :message "must be a string"})
    (blank-string? v) (conj errors {:field field :message "must not be blank"})
    (> (count (str/trim v)) max-length)
    (conj errors {:field field :message (str "must be at most " max-length " characters")})
    :else errors))

(defn- integer-like
  "Return the integer value of `v` when it is an integer, or a string holding
  one. Returns ::invalid otherwise."
  [v]
  (cond
    (integer? v) v
    (string? v)  (try (Long/parseLong (str/trim v))
                      (catch NumberFormatException _ ::invalid))
    :else        ::invalid))

(defn- check-year [errors v]
  (if (nil? v)
    errors
    (let [n (integer-like v)]
      (cond
        (= ::invalid n) (conj errors {:field "year" :message "must be an integer"})
        (or (< n min-year) (> n max-year))
        (conj errors {:field "year"
                      :message (str "must be between " min-year " and " max-year)})
        :else errors))))

(defn- check-isbn [errors v]
  (cond
    (nil? v)           errors
    (not (string? v))  (conj errors {:field "isbn" :message "must be a string"})
    (blank-string? v)  (conj errors {:field "isbn" :message "must not be blank"})
    (> (count (str/trim v)) 32)
    (conj errors {:field "isbn" :message "must be at most 32 characters"})
    :else errors))

(defn validate-book
  "Validate a decoded JSON book payload.

  Returns `{:book {...}}` with trimmed/coerced values on success, or
  `{:errors [{:field .. :message ..} ..]}` on failure. Title and author are
  required; year and isbn are optional."
  [payload]
  (if-not (map? payload)
    {:errors [{:field "body" :message "must be a JSON object"}]}
    (let [{:keys [title author year isbn]} payload
          errors (-> []
                     (check-required-text "title" title max-title-length)
                     (check-required-text "author" author max-author-length)
                     (check-year year)
                     (check-isbn isbn))]
      (if (seq errors)
        {:errors errors}
        {:book {:title  (trimmed title)
                :author (trimmed author)
                :year   (when (some? year) (integer-like year))
                :isbn   (trimmed isbn)}}))))

(defn parse-id
  "Coerce a path-parameter id to a positive long, or nil when it is not one."
  [s]
  (let [n (integer-like s)]
    (when (and (not= ::invalid n) (pos? n))
      n)))
