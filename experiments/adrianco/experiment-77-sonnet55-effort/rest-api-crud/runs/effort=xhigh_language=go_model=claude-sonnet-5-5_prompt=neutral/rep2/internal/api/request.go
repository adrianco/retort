package api

import (
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"reflect"
	"strings"
	"unicode/utf8"

	"bookapi/internal/store"
)

const (
	maxBodyBytes  = 1 << 20
	maxTitleLen   = 255
	maxAuthorLen  = 255
	maxISBNLen    = 32
	minYear       = 1
	maxYear       = 9999
	invalidBody   = "invalid request body"
	validationMsg = "validation failed"
)

// bookRequest is the JSON body accepted by POST /books and PUT /books/{id}.
// Unknown fields (such as "id") are ignored.
type bookRequest struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   *int   `json:"year"`
	ISBN   string `json:"isbn"`
}

// readBook decodes and validates a book from the request body. On failure it
// writes the error response and returns false.
func readBook(w http.ResponseWriter, r *http.Request) (store.Input, bool) {
	var req bookRequest
	if !decodeJSON(w, r, &req) {
		return store.Input{}, false
	}
	in, problems := req.validate()
	if len(problems) > 0 {
		writeErrorDetails(w, http.StatusBadRequest, validationMsg, problems)
		return store.Input{}, false
	}
	return in, true
}

// validate trims and checks the request, returning the normalized input or a
// per-field map of problems.
func (b bookRequest) validate() (store.Input, map[string]string) {
	problems := map[string]string{}

	title := strings.TrimSpace(b.Title)
	switch {
	case title == "":
		problems["title"] = "is required"
	case utf8.RuneCountInString(title) > maxTitleLen:
		problems["title"] = "must be at most 255 characters"
	}

	author := strings.TrimSpace(b.Author)
	switch {
	case author == "":
		problems["author"] = "is required"
	case utf8.RuneCountInString(author) > maxAuthorLen:
		problems["author"] = "must be at most 255 characters"
	}

	if b.Year != nil && (*b.Year < minYear || *b.Year > maxYear) {
		problems["year"] = "must be between 1 and 9999"
	}

	isbn := strings.TrimSpace(b.ISBN)
	if utf8.RuneCountInString(isbn) > maxISBNLen {
		problems["isbn"] = "must be at most 32 characters"
	}

	return store.Input{Title: title, Author: author, Year: b.Year, ISBN: isbn}, problems
}

var errTrailingData = errors.New("unexpected data after JSON body")

// decodeJSON reads exactly one JSON value from the body into dst. On failure
// it writes the error response and returns false.
func decodeJSON(w http.ResponseWriter, r *http.Request, dst any) bool {
	r.Body = http.MaxBytesReader(w, r.Body, maxBodyBytes)
	dec := json.NewDecoder(r.Body)

	err := dec.Decode(dst)
	if err == nil {
		// Anything after the first value (other than whitespace) is an error.
		if _, extra := dec.Token(); extra != io.EOF {
			err = errTrailingData
		}
	}
	if err == nil {
		return true
	}

	var (
		maxErr    *http.MaxBytesError
		typeErr   *json.UnmarshalTypeError
		syntaxErr *json.SyntaxError
	)
	switch {
	case errors.As(err, &maxErr):
		writeError(w, http.StatusRequestEntityTooLarge, "request body too large")
	case errors.Is(err, io.EOF):
		writeError(w, http.StatusBadRequest, "request body is empty")
	case errors.As(err, &typeErr):
		if typeErr.Field == "" {
			writeError(w, http.StatusBadRequest, "request body must be a JSON object")
		} else {
			writeErrorDetails(w, http.StatusBadRequest, invalidBody,
				map[string]string{typeErr.Field: "has the wrong type (expected " + expectedType(typeErr) + ")"})
		}
	case errors.Is(err, errTrailingData):
		writeError(w, http.StatusBadRequest, "request body must contain a single JSON object")
	case errors.As(err, &syntaxErr), errors.Is(err, io.ErrUnexpectedEOF):
		writeError(w, http.StatusBadRequest, "malformed JSON")
	default:
		writeError(w, http.StatusBadRequest, invalidBody)
	}
	return false
}

// expectedType names the JSON type a field was expected to have.
func expectedType(e *json.UnmarshalTypeError) string {
	switch e.Type.Kind() {
	case reflect.String:
		return "string"
	case reflect.Int, reflect.Int64:
		return "integer"
	default:
		return e.Type.String()
	}
}
