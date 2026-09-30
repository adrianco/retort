package api

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"reflect"

	"bookapi/internal/book"
)

// maxBodyBytes caps the size of a request body. A valid book is a couple of
// kilobytes at most.
const maxBodyBytes = 1 << 20

var errTrailingData = errors.New("data after the JSON value")

// errorBody is the JSON shape of every error response. Details maps field names
// to problems and is only present for validation failures.
type errorBody struct {
	Error   string            `json:"error"`
	Details map[string]string `json:"details,omitempty"`
}

const internalErrorBody = `{"error":"internal server error"}` + "\n"

// writeJSON sends v as a JSON response with the given status.
func (s *server) writeJSON(w http.ResponseWriter, status int, v any) {
	var buf bytes.Buffer
	enc := json.NewEncoder(&buf)
	enc.SetEscapeHTML(false) // keep "Tom & Jerry" readable; the body is JSON, not HTML
	if err := enc.Encode(v); err != nil {
		s.log.Error("encode response", "err", err)
		status = http.StatusInternalServerError
		buf.Reset()
		buf.WriteString(internalErrorBody)
	}

	h := w.Header()
	h.Set("Content-Type", "application/json")
	h.Set("X-Content-Type-Options", "nosniff")
	w.WriteHeader(status)
	w.Write(buf.Bytes())
}

func (s *server) writeError(w http.ResponseWriter, status int, message string) {
	s.writeJSON(w, status, errorBody{Error: message})
}

// writeValidationError answers 400 and names each offending field.
func (s *server) writeValidationError(w http.ResponseWriter, err error) {
	var fields book.ValidationError
	errors.As(err, &fields) // any other error kind simply has no per-field details
	details := make(map[string]string, len(fields))
	for _, fe := range fields {
		details[fe.Field] = fe.Message
	}
	s.writeJSON(w, http.StatusBadRequest, errorBody{Error: err.Error(), Details: details})
}

// decodeInput reads, normalizes and validates the book in the request body. On
// failure it writes the error response itself and reports false.
func (s *server) decodeInput(w http.ResponseWriter, r *http.Request) (book.Input, bool) {
	var in book.Input
	if err := decodeJSON(w, r, &in); err != nil {
		var tooLarge *http.MaxBytesError
		if errors.As(err, &tooLarge) {
			s.writeError(w, http.StatusRequestEntityTooLarge, "request body too large")
		} else {
			s.writeError(w, http.StatusBadRequest, describeBodyError(err))
		}
		return book.Input{}, false
	}

	in = in.Normalized()
	if err := in.Validate(); err != nil {
		s.writeValidationError(w, err)
		return book.Input{}, false
	}
	return in, true
}

// decodeJSON reads exactly one JSON value from the request body into dst.
// Unknown fields, such as a client-supplied "id", are ignored.
func decodeJSON(w http.ResponseWriter, r *http.Request, dst any) error {
	r.Body = http.MaxBytesReader(w, r.Body, maxBodyBytes)
	dec := json.NewDecoder(r.Body)
	if err := dec.Decode(dst); err != nil {
		return err
	}
	switch err := dec.Decode(&struct{}{}); {
	case errors.Is(err, io.EOF):
		return nil
	case err == nil:
		return errTrailingData
	default:
		return err
	}
}

// describeBodyError turns a decoding failure into a message for API clients
// that does not expose Go type names.
func describeBodyError(err error) string {
	var syntaxErr *json.SyntaxError
	var typeErr *json.UnmarshalTypeError
	switch {
	case errors.Is(err, io.EOF):
		return "request body must not be empty"
	case errors.Is(err, io.ErrUnexpectedEOF):
		return "request body contains truncated JSON"
	case errors.As(err, &syntaxErr):
		return fmt.Sprintf("request body contains invalid JSON (at offset %d)", syntaxErr.Offset)
	case errors.Is(err, errTrailingData):
		return "request body must contain a single JSON object"
	case errors.As(err, &typeErr):
		if typeErr.Field == "" {
			return "request body must be a JSON object"
		}
		return fmt.Sprintf("field %q must be %s", typeErr.Field, jsonType(typeErr.Type))
	default:
		return "request body could not be read"
	}
}

func jsonType(t reflect.Type) string {
	switch t.Kind() {
	case reflect.String:
		return "a string"
	case reflect.Int, reflect.Int8, reflect.Int16, reflect.Int32, reflect.Int64:
		return "an integer"
	default:
		return "of a different type"
	}
}
