(ns ring.mock.request
  "Functions to create mock request maps."
  (:require [cheshire.core :as json]
            [clojure.string :as string]
            [ring.util.codec :as codec]
            [ring.util.mime-type :as mime])
  (:import [java.io ByteArrayInputStream ByteArrayOutputStream File InputStream]
           [java.net URI]
           [java.nio.charset Charset]
           [java.util Map]
           [org.apache.hc.core5.http ContentType HttpEntity]
           [org.apache.hc.client5.http.entity.mime MultipartEntityBuilder]))

(defn- encode-params [params]
  (when params (codec/form-encode params)))

(defn header
  "Add a HTTP header to the request map."
  [request header value]
  (let [header (string/lower-case (name header))]
    (assoc-in request [:headers header] (str value))))

(defn cookie
  "Add a cookie to the request headers map"
  [request cookie-name value]
  (let [cookie-name (name cookie-name)
        cookie-string (str cookie-name "=" value)]
    (update-in request [:headers "cookie"]
               (fn [cookie-header]
                 (if cookie-header
                   (str cookie-header "; " cookie-string)
                   cookie-string)))))

(defn content-type
  "Set the content type of the request map."
  [request mime-type]
  (-> request
      (assoc :content-type mime-type)
      (header :content-type mime-type)))

(defn content-length
  "Set the content length of the request map."
  [request length]
  (-> request
      (assoc :content-length length)
      (header :content-length length)))

(defn- combined-query [request params]
  (let [query (:query-string request)]
    (when (or query params)
      (string/join "&"
        (remove string/blank?
                [query (encode-params params)])))))

(defn- merge-query [request params]
  (if-let [qs (combined-query request params)]
    (assoc request :query-string qs)
    request))

(defn query-string
  "Set the query string of the request to a string or a map of parameters."
  [request params]
  (cond
    (nil? params) request
    (map? params) (assoc request :query-string (encode-params params))
    :else (assoc request :query-string params)))

(defmulti body
  "Set the body of the request. The supplied body value can be a string or
  a map of parameters to be url-encoded."
  {:arglists '([request body-value])}
  (fn [_request x] (type x)))

(defmethod body String [request ^String string]
  (body request (.getBytes string)))

(defmethod body (class (byte-array 0)) [request bytes]
  (-> request
      (content-length (count bytes))
      (assoc :body (ByteArrayInputStream. bytes))))

(defmethod body Map [request params]
  (-> request
      (content-type "application/x-www-form-urlencoded")
      (body (encode-params params))))

(defmethod body nil [request _params]
  request)

(defn json-body
  "Set the body of the request to a JSON structure. The supplied body value
  should be a map of parameters to be converted to JSON."
  [request body-value]
  (-> request
      (content-type "application/json")
      (body (json/generate-string body-value))))

(def ^:private default-charset
  (Charset/forName "UTF-8"))

(defn- file? [f]
  (instance? File f))

(defn- str->bytes ^bytes [^String s]
  (.getBytes s ^Charset default-charset))

(defn- add-binary-body
  [^MultipartEntityBuilder builder key value ^ContentType mimetype
   ^String filename]
  (let [k (name key)]
    (cond
      (string? value)
      (.addBinaryBody builder k (str->bytes value) mimetype filename)
      (bytes? value)
      (.addBinaryBody builder k ^bytes value mimetype filename)
      (file? value)
      (.addBinaryBody builder k ^File value mimetype filename)
      (instance? InputStream value)
      (.addBinaryBody builder k ^InputStream value mimetype filename)
      :else
      (throw (IllegalArgumentException.
               (str "Cannot encode a value of type " (type value)
                    " as a multipart body."))))))

(defn- add-multipart-part [^MultipartEntityBuilder builder k v]
  (let [param    (if (map? v) v {:value v})
        value    (if (map? v) (:value v) v)
        mimetype (ContentType/parse
                  (or (:content-type param)
                      (when (file? value)
                        (mime/ext-mime-type (.getName ^File value)))
                      (if (string? (:value param))
                        "text/plain; charset=UTF-8"
                        "application/octet-stream")))
        filename (or (:filename param)
                     (when (file? value) (.getName ^File value)))]
    (add-binary-body builder (name k) value mimetype filename)))

(defn- multipart-entity ^HttpEntity [params]
  (let [builder (MultipartEntityBuilder/create)]
    (.setCharset builder ^Charset default-charset)
    (doseq [[k v] params]
      (add-multipart-part builder k v))
    (.build builder)))

(defn multipart-body
  "Set the body of the request to a map of parameters encoded as a multipart
  form. The parameters are supplied as a map. The keys should be keywords or
  strings. The values should be maps that contain the following keys:

    :value        - a string, byte array, File or InputStream
    :filename     - the name of the file the value came from (optional)
    :content-type - the content type of the value (optional)

  The value may also be a string, byte array, File or InputStream instead of a
  map. In that case, it will be treated as if it were a map with a single :value
  key."
  [request params]
  (let [entity (multipart-entity params)
        out    (ByteArrayOutputStream.)]
    (.writeTo entity out)
    (.close out)
    (-> request
        (content-length (.getContentLength entity))
        (content-type (.getContentType entity))
        (assoc :body (ByteArrayInputStream. (.toByteArray out))))))

(def default-port
  "A map of the default ports for a scheme."
  {:http 80
   :https 443})

(defn request
  "Create a minimal valid request map from a HTTP method keyword, a string
  containing a URI, and an optional map of parameters that will be added to
  the query string of the URI. The URI can be relative or absolute. Relative
  URIs are assumed to go to http://localhost."
  ([method uri]
     (request method uri nil))
  ([method uri params]
     (let [uri    (URI. uri)
           scheme (keyword (or (.getScheme uri) "http"))
           host   (or (.getHost uri) "localhost")
           port   (when (not= (.getPort uri) -1) (.getPort uri))
           path   (.getRawPath uri)
           query  (.getRawQuery uri)
           request {:protocol       "HTTP/1.1"
                    :server-port    (or port (default-port scheme))
                    :server-name    host
                    :remote-addr    "127.0.0.1"
                    :uri            (if (string/blank? path) "/" path)
                    :scheme         scheme
                    :request-method method
                    :headers        {"host" (if port
                                              (str host ":" port)
                                              host)}}
           request (if query
                     (assoc request :query-string query)
                     request)]
       (if (#{:get :head :delete} method)
         (merge-query request params)
         (body request params)))))
