package api

import (
	"encoding/json"
	"net/http"
	"strings"
)

// errorBody is the JSON shape of every error response.
type errorBody struct {
	Error   string            `json:"error"`
	Details map[string]string `json:"details,omitempty"`
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	body, err := json.Marshal(v)
	if err != nil {
		status = http.StatusInternalServerError
		body = []byte(`{"error":"internal server error"}`)
	}
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	w.Write(append(body, '\n'))
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, errorBody{Error: msg})
}

// methodNotAllowed responds 405 with an Allow header listing the supported
// methods. It is registered without a method so it only catches the requests
// that no method-specific route claimed.
func methodNotAllowed(allowed ...string) http.HandlerFunc {
	allow := strings.Join(allowed, ", ")
	return func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Allow", allow)
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
	}
}
