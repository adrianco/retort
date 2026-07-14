(ns books.validation
  "Input validation for book payloads.")

(defn- blank-string? [v]
  (or (nil? v)
      (and (string? v) (clojure.string/blank? v))
      (not (string? v))))

(defn validate-book
  "Validate a book payload. Returns a map of {field message} for any errors,
   or an empty map when the payload is valid.

   Rules:
   - title  : required, non-blank string
   - author : required, non-blank string
   - year   : optional, but must be an integer when present
   - isbn   : optional, but must be a string when present"
  [{:keys [title author year isbn]}]
  (cond-> {}
    (blank-string? title)  (assoc :title "title is required and must be a non-empty string")
    (blank-string? author) (assoc :author "author is required and must be a non-empty string")
    (and (some? year) (not (integer? year)))
    (assoc :year "year must be an integer")
    (and (some? isbn) (not (string? isbn)))
    (assoc :isbn "isbn must be a string")))
