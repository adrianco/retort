package api

import (
	"encoding/json"
	"errors"
	"io"
	"mime"
	"net/http"
	"strings"
)

// maxRequestBody caps how much of a request body we are willing to read. A
// book record is a few hundred bytes; 64 KiB is generous.
const maxRequestBody = 64 << 10

// decodeJSONBody reads a single JSON object from the request into dst.
//
// It is strict on purpose — wrong content type, trailing garbage and misspelled
// field names are all reported rather than silently ignored, so a typo like
// "titel" fails loudly instead of creating a book with no title. Every error it
// returns is a *statusError carrying a client-facing message.
func decodeJSONBody(w http.ResponseWriter, r *http.Request, dst any) error {
	if err := requireJSONContentType(r); err != nil {
		return err
	}

	r.Body = http.MaxBytesReader(w, r.Body, maxRequestBody)
	decoder := json.NewDecoder(r.Body)
	decoder.DisallowUnknownFields()

	if err := decoder.Decode(dst); err != nil {
		return decodeError(err)
	}
	// A well-formed request holds exactly one object; anything after it is a
	// sign the client is sending something we would misinterpret.
	if err := decoder.Decode(&struct{}{}); !errors.Is(err, io.EOF) {
		return errorf(http.StatusBadRequest, "request body must contain a single JSON object")
	}
	return nil
}

func requireJSONContentType(r *http.Request) error {
	header := r.Header.Get("Content-Type")
	if header == "" {
		return errorf(http.StatusUnsupportedMediaType, "Content-Type header is required and must be application/json")
	}
	mediaType, _, err := mime.ParseMediaType(header)
	if err != nil || mediaType != "application/json" {
		return errorf(http.StatusUnsupportedMediaType, "Content-Type must be application/json, got %q", header)
	}
	return nil
}

// decodeError turns the assorted things encoding/json can fail with into a
// message that tells the client what to fix.
func decodeError(err error) error {
	var (
		syntaxErr   *json.SyntaxError
		typeErr     *json.UnmarshalTypeError
		maxBytesErr *http.MaxBytesError
	)
	switch {
	case errors.As(err, &maxBytesErr):
		return errorf(http.StatusRequestEntityTooLarge, "request body must not exceed %d bytes", maxBytesErr.Limit)

	case errors.As(err, &syntaxErr):
		return errorf(http.StatusBadRequest, "request body contains malformed JSON at position %d", syntaxErr.Offset)

	case errors.As(err, &typeErr):
		if typeErr.Field != "" {
			return errorf(http.StatusBadRequest, "field %q must be of type %s", typeErr.Field, typeErr.Type)
		}
		return errorf(http.StatusBadRequest, "request body must be a JSON object")

	case errors.Is(err, io.ErrUnexpectedEOF):
		return errorf(http.StatusBadRequest, "request body contains malformed JSON")

	case errors.Is(err, io.EOF):
		return errorf(http.StatusBadRequest, "request body must not be empty")

	// encoding/json reports unknown fields with a plain error value, so the
	// field name has to be recovered from the text.
	case strings.HasPrefix(err.Error(), "json: unknown field "):
		field := strings.TrimPrefix(err.Error(), "json: unknown field ")
		return errorf(http.StatusBadRequest, "request body contains unknown field %s", field)

	default:
		return errorf(http.StatusBadRequest, "request body could not be decoded: %s", err)
	}
}
