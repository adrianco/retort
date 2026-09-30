package api_test

import (
	"bufio"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"bookapi/internal/api"
	"bookapi/internal/book"
)

// FuzzCreateBookBody feeds arbitrary bytes to POST /books. Whatever arrives,
// the service must answer 201, 400 or 413 with valid JSON, and everything it
// accepts must satisfy the validation rules and be stored normalized.
//
// A plain `go test` replays the seed inputs below; explore further with
//
//	go test -run '^$' -fuzz FuzzCreateBookBody ./internal/api
func FuzzCreateBookBody(f *testing.F) {
	for _, seed := range []string{
		dune, `{}`, `null`, `[]`, `"x"`, `0`, ``, `{`, `{"title":"T","author":"A"} x`,
		`{"title":"T","author":"A","year":1e400}`, `{"title":"T","author":"A","year":-0}`,
		"{\"title\":\"\xff\xfe\",\"author\":\"A\"}", `{"title":"\ud800","author":"A"}`,
		`{"title":"a\u0000b","author":"A"}`, `{"title":"T","author":"A","year":99999999999999999999}`,
		`{"title":{"a":[1,2,{"b":null}]},"author":"A"}`,
	} {
		f.Add(seed)
	}
	// White space beyond ASCII, built from its code point so that it is visible here.
	f.Add(bookJSON("  x  ", noBreakSpace+"y"+noBreakSpace))

	h := api.New(openStore(f), discardLogger())
	f.Fuzz(func(t *testing.T, body string) {
		rec := send(t, h, http.MethodPost, "/books", body)
		switch rec.Code {
		case http.StatusCreated:
			var got book.Book
			if err := json.Unmarshal(rec.Body.Bytes(), &got); err != nil {
				t.Fatalf("201 with invalid JSON %q: %v", rec.Body, err)
			}
			if err := got.Input.Validate(); err != nil || got.ID <= 0 {
				t.Fatalf("accepted body %q as %+v; validation says %v", body, got, err)
			}
			if got.Input != got.Input.Normalize() {
				t.Fatalf("stored a book that was not normalized, %+v, from %q", got, body)
			}
		case http.StatusBadRequest, http.StatusRequestEntityTooLarge:
			var e errorResponse
			if err := json.Unmarshal(rec.Body.Bytes(), &e); err != nil || e.Error == "" {
				t.Fatalf("%d without a JSON error for %q: %q (%v)", rec.Code, body, rec.Body, err)
			}
		default:
			t.Fatalf("status %d for body %q: %s", rec.Code, body, rec.Body)
		}
	})
}

// FuzzRequestTarget sends arbitrary request targets (path and query string) to
// the read endpoints and to DELETE. Whatever arrives, the service must not
// answer with a server error, and a response that claims to be JSON must be.
//
//	go test -run '^$' -fuzz FuzzRequestTarget ./internal/api
func FuzzRequestTarget(f *testing.F) {
	for _, seed := range []string{
		"/books", "/books/1", "/books/", "/health", "/", "/books?author=Alan", "/books?author=%",
		"/books?author=a;b", "/books/%31", "/books/%zz", "/books//1", "/books/../health", "/books/01",
		"/books/9223372036854775808", "/books?%zz=1", "/books?author=%00", "/%", "/books/1/2", "*",
	} {
		f.Add(seed, "GET")
		f.Add(seed, "DELETE")
	}

	h := api.New(openStore(f), discardLogger())
	f.Fuzz(func(t *testing.T, target, method string) {
		switch method {
		case "GET", "HEAD", "PUT", "DELETE":
		default:
			return
		}
		// Go through the request parser, so that only targets a real server
		// would accept get this far.
		raw := method + " " + target + " HTTP/1.1\r\nHost: test\r\n\r\n"
		req, err := http.ReadRequest(bufio.NewReader(strings.NewReader(raw)))
		if err != nil {
			return
		}
		rec := httptest.NewRecorder()
		h.ServeHTTP(rec, req)
		if rec.Code >= 500 {
			t.Fatalf("%s %q answered %d: %s", method, target, rec.Code, rec.Body)
		}
		if method != "HEAD" && strings.HasPrefix(rec.Header().Get("Content-Type"), "application/json") && !json.Valid(rec.Body.Bytes()) {
			t.Fatalf("%s %q claims JSON but sent %q", method, target, rec.Body)
		}
	})
}
