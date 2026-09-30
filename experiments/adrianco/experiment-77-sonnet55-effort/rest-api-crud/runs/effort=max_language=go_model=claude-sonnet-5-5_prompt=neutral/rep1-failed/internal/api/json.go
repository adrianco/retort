package api

import (
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"reflect"

	"bookapi/internal/book"
)

// maxBodyBytes caps request bodies; a book needs a few hundred bytes at most.
const maxBodyBytes = 1 << 20

var errTrailingData = errors.New("request body must contain a single JSON object")

// errorBody is the JSON shape of every error response. Details is only set for
// validation failures, one entry per rejected field.
type errorBody struct {
	Error   string            `json:"error"`
	Details []book.FieldError `json:"details,omitempty"`
}

func (s *server) writeJSON(w http.ResponseWriter, status int, v any) {
	h := w.Header()
	h.Set("Content-Type", "application/json")
	h.Set("X-Content-Type-Options", "nosniff")
	w.WriteHeader(status)

	enc := json.NewEncoder(w)
	enc.SetEscapeHTML(false) // titles like "Q&A" should stay readable
	if err := enc.Encode(v); err != nil {
		// Almost always the client went away before reading its response.
		s.logger.Warn("write response", "err", err)
	}
}

func (s *server) writeError(w http.ResponseWriter, status int, message string) {
	s.writeJSON(w, status, errorBody{Error: message})
}

// decodeInput reads the request body as a book, then normalizes and validates
// it. When ok is false the error response has already been written.
func (s *server) decodeInput(w http.ResponseWriter, r *http.Request) (in book.Input, ok bool) {
	dec := json.NewDecoder(http.MaxBytesReader(w, r.Body, maxBodyBytes))
	err := dec.Decode(&in)
	if err == nil {
		// The body must hold exactly one JSON value.
		err = dec.Decode(&struct{}{})
		switch {
		case err == nil:
			err = errTrailingData
		case errors.Is(err, io.EOF):
			err = nil
		}
	}
	if err != nil {
		s.writeDecodeError(w, err)
		return in, false
	}

	in = in.Normalize()
	if err := in.Validate(); err != nil {
		body := errorBody{Error: err.Error()}
		var verr *book.ValidationError
		if errors.As(err, &verr) {
			body.Details = verr.Fields
		}
		s.writeJSON(w, http.StatusBadRequest, body)
		return in, false
	}
	return in, true
}

// writeDecodeError turns a JSON decoding failure into a client-friendly 4xx
// response without leaking Go type names.
func (s *server) writeDecodeError(w http.ResponseWriter, err error) {
	var (
		tooLarge *http.MaxBytesError
		syntax   *json.SyntaxError
		typeErr  *json.UnmarshalTypeError
	)
	switch {
	case errors.As(err, &tooLarge):
		s.writeError(w, http.StatusRequestEntityTooLarge,
			fmt.Sprintf("request body must not exceed %d bytes", tooLarge.Limit))
	case errors.Is(err, io.EOF):
		s.writeError(w, http.StatusBadRequest, "request body must not be empty")
	case errors.Is(err, io.ErrUnexpectedEOF):
		s.writeError(w, http.StatusBadRequest, "request body is not valid JSON: unexpected end of input")
	case errors.As(err, &syntax):
		s.writeError(w, http.StatusBadRequest, "request body is not valid JSON: "+syntax.Error())
	case errors.As(err, &typeErr) && typeErr.Field == "":
		s.writeError(w, http.StatusBadRequest, "request body must be a JSON object")
	case errors.As(err, &typeErr):
		s.writeError(w, http.StatusBadRequest,
			fmt.Sprintf("field %q must be %s, got %s", typeErr.Field, jsonKind(typeErr.Type), typeErr.Value))
	case errors.Is(err, errTrailingData):
		s.writeError(w, http.StatusBadRequest, err.Error())
	default:
		s.writeError(w, http.StatusBadRequest, "request body could not be read")
	}
}

// jsonKind names the JSON type that decoding into t expects. book.Input has
// only string and integer fields.
func jsonKind(t reflect.Type) string {
	if t.Kind() == reflect.String {
		return "a string"
	}
	return "an integer"
}
