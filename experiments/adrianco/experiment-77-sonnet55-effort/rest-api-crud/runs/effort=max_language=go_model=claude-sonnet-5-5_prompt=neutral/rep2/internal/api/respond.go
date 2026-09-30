package api

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"

	"bookapi/internal/book"
)

// maxBodyBytes caps request bodies; a book is a few hundred bytes at most.
const maxBodyBytes = 1 << 20

// errNotObject covers a body that is not exactly one JSON object: an array, a
// bare scalar, or an object followed by more data.
var errNotObject = errors.New("request body must be a single JSON object")

// errorBody is the JSON shape of every error response. Details is set for
// validation failures and maps each rejected field to the reason.
type errorBody struct {
	Error   string            `json:"error"`
	Details map[string]string `json:"details,omitempty"`
}

// writeJSON sends v as a JSON response. The body is encoded before anything is
// written so an encoding failure can still produce a clean 500.
func writeJSON(w http.ResponseWriter, status int, v any) {
	var buf bytes.Buffer
	enc := json.NewEncoder(&buf)
	enc.SetEscapeHTML(false) // keep titles like "Q&A" readable in curl output
	if err := enc.Encode(v); err != nil {
		// Cannot happen for the plain structs and maps this package sends; kept
		// so that a future mistake still yields a well-formed error response.
		status = http.StatusInternalServerError
		buf.Reset()
		buf.WriteString(`{"error":"internal server error"}` + "\n")
	}

	h := w.Header()
	h.Set("Content-Type", "application/json")
	h.Set("X-Content-Type-Options", "nosniff")
	w.WriteHeader(status)
	w.Write(buf.Bytes())
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, errorBody{Error: msg})
}

// decodeInput reads, normalises and validates the book in the request body.
// When the request is unacceptable it writes the error response itself and
// returns false.
func decodeInput(w http.ResponseWriter, r *http.Request) (book.Input, bool) {
	var in book.Input
	if !decodeJSON(w, r, &in) {
		return in, false
	}

	in.Normalize()
	if err := in.Validate(); err != nil {
		var details book.ValidationError // Validate only ever returns this type
		errors.As(err, &details)
		writeJSON(w, http.StatusBadRequest, errorBody{Error: "validation failed", Details: details})
		return in, false
	}
	return in, true
}

// decodeJSON decodes the request body, which must hold exactly one JSON value,
// into dst. On failure it writes the error response and returns false.
func decodeJSON(w http.ResponseWriter, r *http.Request, dst any) bool {
	r.Body = http.MaxBytesReader(w, r.Body, maxBodyBytes)
	dec := json.NewDecoder(r.Body)

	err := dec.Decode(dst)
	if err == nil {
		switch extra := dec.Decode(&struct{}{}); {
		case errors.Is(extra, io.EOF):
			return true
		case extra == nil:
			err = errNotObject
		default:
			err = extra
		}
	}

	var (
		tooLarge *http.MaxBytesError
		syntax   *json.SyntaxError
		typeErr  *json.UnmarshalTypeError
	)
	switch {
	case errors.As(err, &tooLarge):
		writeError(w, http.StatusRequestEntityTooLarge,
			fmt.Sprintf("request body must not exceed %d bytes", tooLarge.Limit))
	case errors.Is(err, io.EOF):
		writeError(w, http.StatusBadRequest, "request body must not be empty")
	case errors.As(err, &syntax), errors.Is(err, io.ErrUnexpectedEOF):
		writeError(w, http.StatusBadRequest, "request body is not valid JSON")
	case errors.As(err, &typeErr) && typeErr.Field != "":
		writeError(w, http.StatusBadRequest,
			fmt.Sprintf("field %q: expected %s but got %s", typeErr.Field, typeErr.Type, typeErr.Value))
	case errors.As(err, &typeErr), errors.Is(err, errNotObject):
		// A type error with no field means the top-level value was not an object.
		writeError(w, http.StatusBadRequest, errNotObject.Error())
	default:
		writeError(w, http.StatusBadRequest, "invalid request body")
	}
	return false
}
