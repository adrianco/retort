package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"slices"
	"strconv"
	"strings"
	"testing"
	"time"
)

// testServer is a real HTTP server on a loopback port, backed by a real
// SQLite file, so these tests exercise routing, decoding, the store and
// encoding together.
type testServer struct {
	*httptest.Server
	t     *testing.T
	store *Store
}

// newTestServer starts a server; each opt adjusts the API before it begins
// serving, so tests can pin the clock without racing the request goroutines.
func newTestServer(t *testing.T, opts ...func(*API)) *testServer {
	t.Helper()

	store := newTestStore(t)
	api := NewAPI(store, nil)
	for _, opt := range opts {
		opt(api)
	}
	srv := httptest.NewServer(api.Routes())
	t.Cleanup(srv.Close)
	return &testServer{Server: srv, t: t, store: store}
}

func withClock(at time.Time) func(*API) {
	return func(a *API) { a.now = func() time.Time { return at } }
}

// response is the decoded outcome of a request.
type response struct {
	status int
	header http.Header
	body   []byte
}

// request sends body as JSON when it is non-empty.
func (ts *testServer) request(method, path, body string) response {
	ts.t.Helper()

	contentType := ""
	if body != "" {
		contentType = "application/json"
	}
	return ts.requestRaw(method, path, contentType, body)
}

func (ts *testServer) requestRaw(method, path, contentType, body string) response {
	ts.t.Helper()

	var reader io.Reader = http.NoBody
	if body != "" {
		reader = strings.NewReader(body)
	}
	req, err := http.NewRequest(method, ts.URL+path, reader)
	if err != nil {
		ts.t.Fatalf("new request %s %s: %v", method, path, err)
	}
	if contentType != "" {
		req.Header.Set("Content-Type", contentType)
	}

	resp, err := ts.Client().Do(req)
	if err != nil {
		ts.t.Fatalf("%s %s: %v", method, path, err)
	}
	defer resp.Body.Close()

	data, err := io.ReadAll(resp.Body)
	if err != nil {
		ts.t.Fatalf("read body of %s %s: %v", method, path, err)
	}
	return response{status: resp.StatusCode, header: resp.Header, body: data}
}

// expect asserts the status code, dumping the body on failure so a mismatch
// is diagnosable from the test output alone.
func (r response) expect(t *testing.T, status int) response {
	t.Helper()

	if r.status != status {
		t.Fatalf("status = %d, want %d; body: %s", r.status, status, r.body)
	}
	if ct := r.header.Get("Content-Type"); status != http.StatusNoContent &&
		!strings.HasPrefix(ct, "application/json") {
		t.Errorf("Content-Type = %q, want application/json", ct)
	}
	return r
}

func (r response) book(t *testing.T) Book {
	t.Helper()

	var b Book
	if err := json.Unmarshal(r.body, &b); err != nil {
		t.Fatalf("decode book from %s: %v", r.body, err)
	}
	return b
}

func (r response) books(t *testing.T) []Book {
	t.Helper()

	var books []Book
	if err := json.Unmarshal(r.body, &books); err != nil {
		t.Fatalf("decode book list from %s: %v", r.body, err)
	}
	return books
}

func (r response) apiError(t *testing.T) ErrorDetail {
	t.Helper()

	var body ErrorBody
	if err := json.Unmarshal(r.body, &body); err != nil {
		t.Fatalf("decode error from %s: %v", r.body, err)
	}
	if body.Error.Code == "" {
		t.Errorf("error body %s has no code", r.body)
	}
	if body.Error.Message == "" {
		t.Errorf("error body %s has no message", r.body)
	}
	return body.Error
}

const goBookJSON = `{
	"title": "The Go Programming Language",
	"author": "Alan A. A. Donovan",
	"year": 2015,
	"isbn": "978-0-13-419044-0"
}`

func TestHealth(t *testing.T) {
	ts := newTestServer(t)

	resp := ts.request(http.MethodGet, "/health", "").expect(t, http.StatusOK)

	var body map[string]string
	if err := json.Unmarshal(resp.body, &body); err != nil {
		t.Fatalf("decode health body %s: %v", resp.body, err)
	}
	if body["status"] != "ok" {
		t.Errorf(`status = %q, want "ok"`, body["status"])
	}
	if body["database"] != "ok" {
		t.Errorf(`database = %q, want "ok"`, body["database"])
	}
}

// TestBookLifecycle walks the whole documented API in the order a client
// would: create, read, list, update, delete.
func TestBookLifecycle(t *testing.T) {
	ts := newTestServer(t)

	created := ts.request(http.MethodPost, "/books", goBookJSON).
		expect(t, http.StatusCreated).book(t)

	if created.ID == 0 {
		t.Fatal("POST /books did not assign an id")
	}
	if created.Title != "The Go Programming Language" || created.Author != "Alan A. A. Donovan" {
		t.Errorf("created book = %+v, want the submitted title and author", created)
	}
	if created.Year == nil || *created.Year != 2015 {
		t.Errorf("created year = %v, want 2015", created.Year)
	}
	if created.ISBN != "9780134190440" {
		t.Errorf("created isbn = %q, want the normalised form", created.ISBN)
	}
	if created.CreatedAt.IsZero() || created.UpdatedAt.IsZero() {
		t.Errorf("created timestamps are zero: %+v", created)
	}

	// 201 must point at the new resource, and that URL must work.
	location := ts.request(http.MethodPost, "/books", `{"title":"Second","author":"Author"}`).
		expect(t, http.StatusCreated).header.Get("Location")
	if location == "" {
		t.Error("POST /books did not set a Location header")
	} else if got := ts.request(http.MethodGet, location, "").expect(t, http.StatusOK).book(t); got.Title != "Second" {
		t.Errorf("GET %s returned %q, want \"Second\"", location, got.Title)
	}

	fetched := ts.request(http.MethodGet, "/books/"+itoa64(created.ID), "").
		expect(t, http.StatusOK).book(t)
	if fetched.ID != created.ID || fetched.Title != created.Title {
		t.Errorf("GET /books/%d = %+v, want %+v", created.ID, fetched, created)
	}

	books := ts.request(http.MethodGet, "/books", "").expect(t, http.StatusOK).books(t)
	if len(books) != 2 {
		t.Fatalf("GET /books returned %d books, want 2", len(books))
	}

	updated := ts.request(http.MethodPut, "/books/"+itoa64(created.ID),
		`{"title":"The Go Programming Language, 2nd ed.","author":"Alan A. A. Donovan","year":2016}`).
		expect(t, http.StatusOK).book(t)
	if updated.ID != created.ID {
		t.Errorf("PUT changed the id: %d, want %d", updated.ID, created.ID)
	}
	if updated.Title != "The Go Programming Language, 2nd ed." {
		t.Errorf("PUT title = %q, want the new title", updated.Title)
	}
	if updated.Year == nil || *updated.Year != 2016 {
		t.Errorf("PUT year = %v, want 2016", updated.Year)
	}
	// PUT replaces the whole record, so the omitted ISBN is cleared.
	if updated.ISBN != "" {
		t.Errorf("PUT isbn = %q, want it cleared by the replacement", updated.ISBN)
	}
	if !updated.CreatedAt.Equal(created.CreatedAt) {
		t.Errorf("PUT created_at = %v, want it preserved as %v", updated.CreatedAt, created.CreatedAt)
	}
	if !updated.UpdatedAt.After(created.UpdatedAt) {
		t.Errorf("PUT updated_at = %v, want it after %v", updated.UpdatedAt, created.UpdatedAt)
	}

	ts.request(http.MethodDelete, "/books/"+itoa64(created.ID), "").expect(t, http.StatusNoContent)

	ts.request(http.MethodGet, "/books/"+itoa64(created.ID), "").expect(t, http.StatusNotFound)
	if remaining := ts.request(http.MethodGet, "/books", "").expect(t, http.StatusOK).books(t); len(remaining) != 1 {
		t.Errorf("after delete, GET /books returned %d books, want 1", len(remaining))
	}
}

func TestCreateBookValidation(t *testing.T) {
	tests := []struct {
		name       string
		body       string
		wantStatus int
		wantCode   string
		wantFields []string
	}{
		{
			name:       "title missing",
			body:       `{"author":"Frank Herbert"}`,
			wantStatus: http.StatusBadRequest,
			wantCode:   "validation_failed",
			wantFields: []string{"title"},
		},
		{
			name:       "author missing",
			body:       `{"title":"Dune"}`,
			wantStatus: http.StatusBadRequest,
			wantCode:   "validation_failed",
			wantFields: []string{"author"},
		},
		{
			name:       "title and author blank",
			body:       `{"title":"  ","author":""}`,
			wantStatus: http.StatusBadRequest,
			wantCode:   "validation_failed",
			wantFields: []string{"title", "author"},
		},
		{
			name:       "empty object",
			body:       `{}`,
			wantStatus: http.StatusBadRequest,
			wantCode:   "validation_failed",
			wantFields: []string{"title", "author"},
		},
		{
			name:       "year out of range",
			body:       `{"title":"Dune","author":"Frank Herbert","year":99}`,
			wantStatus: http.StatusBadRequest,
			wantCode:   "validation_failed",
			wantFields: []string{"year"},
		},
		{
			name:       "isbn invalid",
			body:       `{"title":"Dune","author":"Frank Herbert","isbn":"1234567890"}`,
			wantStatus: http.StatusBadRequest,
			wantCode:   "validation_failed",
			wantFields: []string{"isbn"},
		},
		{
			name:       "malformed json",
			body:       `{"title":"Dune",`,
			wantStatus: http.StatusBadRequest,
			wantCode:   "invalid_json",
		},
		{
			name:       "wrong type for year",
			body:       `{"title":"Dune","author":"Frank Herbert","year":"1965"}`,
			wantStatus: http.StatusBadRequest,
			wantCode:   "invalid_json",
		},
		{
			name:       "body is an array",
			body:       `[{"title":"Dune","author":"Frank Herbert"}]`,
			wantStatus: http.StatusBadRequest,
			wantCode:   "invalid_json",
		},
		{
			name:       "unknown field",
			body:       `{"title":"Dune","author":"Frank Herbert","publisher":"Chilton"}`,
			wantStatus: http.StatusBadRequest,
			wantCode:   "invalid_json",
		},
		{
			name:       "two json objects",
			body:       `{"title":"Dune","author":"Frank Herbert"}{"title":"x","author":"y"}`,
			wantStatus: http.StatusBadRequest,
			wantCode:   "invalid_json",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			ts := newTestServer(t)

			resp := ts.request(http.MethodPost, "/books", tt.body).expect(t, tt.wantStatus)
			detail := resp.apiError(t)
			if detail.Code != tt.wantCode {
				t.Errorf("error code = %q, want %q", detail.Code, tt.wantCode)
			}
			if tt.wantFields != nil {
				if got := fieldNames(detail.Fields); !slices.Equal(got, tt.wantFields) {
					t.Errorf("error fields = %v, want %v", got, tt.wantFields)
				}
			}

			// A rejected request must not have written anything.
			if books := ts.request(http.MethodGet, "/books", "").books(t); len(books) != 0 {
				t.Errorf("after a rejected POST the collection holds %d books, want 0", len(books))
			}
		})
	}
}

func TestCreateBookEmptyBody(t *testing.T) {
	ts := newTestServer(t)

	resp := ts.request(http.MethodPost, "/books", "").expect(t, http.StatusBadRequest)
	if code := resp.apiError(t).Code; code != "invalid_json" {
		t.Errorf("error code = %q, want \"invalid_json\"", code)
	}
}

func TestCreateBookUnsupportedMediaType(t *testing.T) {
	ts := newTestServer(t)

	resp := ts.requestRaw(http.MethodPost, "/books", "text/plain", goBookJSON).
		expect(t, http.StatusUnsupportedMediaType)
	if code := resp.apiError(t).Code; code != "unsupported_media_type" {
		t.Errorf("error code = %q, want \"unsupported_media_type\"", code)
	}

	// A charset parameter on an otherwise correct type is fine.
	ts.requestRaw(http.MethodPost, "/books", "application/json; charset=utf-8", goBookJSON).
		expect(t, http.StatusCreated)
}

func TestCreateBookOversizedBody(t *testing.T) {
	ts := newTestServer(t)

	// Valid JSON, but larger than the handler accepts.
	body := `{"title":"` + strings.Repeat("x", maxBodyBytes) + `","author":"Someone"}`
	resp := ts.request(http.MethodPost, "/books", body).expect(t, http.StatusRequestEntityTooLarge)
	if code := resp.apiError(t).Code; code != "request_too_large" {
		t.Errorf("error code = %q, want \"request_too_large\"", code)
	}
}

// The upper year bound is relative to the server's clock, so it is checked
// against a pinned one rather than whatever year the suite happens to run in.
func TestCreateBookYearBoundIsRelativeToClock(t *testing.T) {
	ts := newTestServer(t, withClock(reference))

	body := func(year int) string {
		return fmt.Sprintf(`{"title":"Forthcoming","author":"Someone","year":%d}`, year)
	}

	// Next year is a legitimate publication date; the year after is not.
	ts.request(http.MethodPost, "/books", body(reference.Year()+1)).expect(t, http.StatusCreated)

	resp := ts.request(http.MethodPost, "/books", body(reference.Year()+2)).
		expect(t, http.StatusBadRequest)
	if got := fieldNames(resp.apiError(t).Fields); !slices.Equal(got, []string{"year"}) {
		t.Errorf("error fields = %v, want [year]", got)
	}
}

func TestCreateBookDuplicateISBN(t *testing.T) {
	ts := newTestServer(t)

	ts.request(http.MethodPost, "/books", goBookJSON).expect(t, http.StatusCreated)

	// The same ISBN written differently must still collide.
	resp := ts.request(http.MethodPost, "/books",
		`{"title":"The Go Programming Language","author":"Brian W. Kernighan","isbn":"9780134190440"}`).
		expect(t, http.StatusConflict)
	if code := resp.apiError(t).Code; code != "isbn_taken" {
		t.Errorf("error code = %q, want \"isbn_taken\"", code)
	}

	// Books without an ISBN are exempt from the uniqueness rule.
	for i := 0; i < 2; i++ {
		ts.request(http.MethodPost, "/books", `{"title":"Untitled","author":"Anonymous"}`).
			expect(t, http.StatusCreated)
	}
}

func TestListBooksAuthorFilter(t *testing.T) {
	ts := newTestServer(t)

	for _, body := range []string{
		`{"title":"Dune","author":"Frank Herbert","year":1965}`,
		`{"title":"Dune Messiah","author":"Frank Herbert","year":1969}`,
		`{"title":"Neuromancer","author":"William Gibson","year":1984}`,
	} {
		ts.request(http.MethodPost, "/books", body).expect(t, http.StatusCreated)
	}

	tests := []struct {
		query string
		want  int
	}{
		{"", 3},
		{"?author=Frank%20Herbert", 2},
		{"?author=frank+herbert", 2}, // case-insensitive
		{"?author=William+Gibson", 1},
		{"?author=Nobody", 0},
		{"?author=", 3}, // an empty filter is no filter
	}

	for _, tt := range tests {
		resp := ts.request(http.MethodGet, "/books"+tt.query, "").expect(t, http.StatusOK)
		if got := len(resp.books(t)); got != tt.want {
			t.Errorf("GET /books%s returned %d books, want %d (body: %s)", tt.query, got, tt.want, resp.body)
		}
	}
}

// An empty collection must encode as [] so clients can iterate it without a
// nil check.
func TestListBooksEmptyIsJSONArray(t *testing.T) {
	ts := newTestServer(t)

	resp := ts.request(http.MethodGet, "/books", "").expect(t, http.StatusOK)
	if got := string(bytes.TrimSpace(resp.body)); got != "[]" {
		t.Errorf("GET /books on an empty collection = %s, want []", got)
	}
}

func TestGetBookErrors(t *testing.T) {
	ts := newTestServer(t)

	tests := []struct {
		path       string
		wantStatus int
		wantCode   string
	}{
		{"/books/999", http.StatusNotFound, "not_found"},
		{"/books/abc", http.StatusBadRequest, "invalid_id"},
		{"/books/0", http.StatusBadRequest, "invalid_id"},
		{"/books/-1", http.StatusBadRequest, "invalid_id"},
		{"/books/1.5", http.StatusBadRequest, "invalid_id"},
		{"/books/99999999999999999999", http.StatusBadRequest, "invalid_id"},
	}

	for _, tt := range tests {
		resp := ts.request(http.MethodGet, tt.path, "").expect(t, tt.wantStatus)
		if code := resp.apiError(t).Code; code != tt.wantCode {
			t.Errorf("GET %s error code = %q, want %q", tt.path, code, tt.wantCode)
		}
	}
}

func TestUpdateBookErrors(t *testing.T) {
	ts := newTestServer(t)

	created := ts.request(http.MethodPost, "/books", goBookJSON).
		expect(t, http.StatusCreated).book(t)
	path := "/books/" + itoa64(created.ID)

	// Missing book.
	resp := ts.request(http.MethodPut, "/books/999", `{"title":"Ghost","author":"Nobody"}`).
		expect(t, http.StatusNotFound)
	if code := resp.apiError(t).Code; code != "not_found" {
		t.Errorf("error code = %q, want \"not_found\"", code)
	}

	// PUT is a replacement, so it enforces the same required fields as POST.
	resp = ts.request(http.MethodPut, path, `{"author":"Alan A. A. Donovan"}`).
		expect(t, http.StatusBadRequest)
	if got := fieldNames(resp.apiError(t).Fields); !slices.Equal(got, []string{"title"}) {
		t.Errorf("error fields = %v, want [title]", got)
	}

	// A rejected update must leave the stored book untouched.
	after := ts.request(http.MethodGet, path, "").expect(t, http.StatusOK).book(t)
	if after.Title != created.Title || after.ISBN != created.ISBN {
		t.Errorf("book after a rejected PUT = %+v, want %+v", after, created)
	}
	if !after.UpdatedAt.Equal(created.UpdatedAt) {
		t.Errorf("updated_at changed on a rejected PUT: %v, want %v", after.UpdatedAt, created.UpdatedAt)
	}
}

func TestUpdateBookISBNConflict(t *testing.T) {
	ts := newTestServer(t)

	first := ts.request(http.MethodPost, "/books", goBookJSON).
		expect(t, http.StatusCreated).book(t)
	second := ts.request(http.MethodPost, "/books",
		`{"title":"The Practice of Programming","author":"Brian W. Kernighan","isbn":"9780201615869"}`).
		expect(t, http.StatusCreated).book(t)

	resp := ts.request(http.MethodPut, "/books/"+itoa64(second.ID),
		`{"title":"The Practice of Programming","author":"Brian W. Kernighan","isbn":"`+first.ISBN+`"}`).
		expect(t, http.StatusConflict)
	if code := resp.apiError(t).Code; code != "isbn_taken" {
		t.Errorf("error code = %q, want \"isbn_taken\"", code)
	}

	// Keeping its own ISBN is not a conflict.
	ts.request(http.MethodPut, "/books/"+itoa64(second.ID),
		`{"title":"The Practice of Programming","author":"Kernighan and Pike","isbn":"`+second.ISBN+`"}`).
		expect(t, http.StatusOK)
}

// Fetching a book and PUTting the same document back — with the read-only
// fields the API itself emitted — has to work, even though unknown fields are
// rejected.
func TestUpdateAcceptsRoundTrippedDocument(t *testing.T) {
	ts := newTestServer(t)

	created := ts.request(http.MethodPost, "/books", goBookJSON).
		expect(t, http.StatusCreated).book(t)
	path := "/books/" + itoa64(created.ID)

	fetched := ts.request(http.MethodGet, path, "").expect(t, http.StatusOK)

	var doc map[string]any
	if err := json.Unmarshal(fetched.body, &doc); err != nil {
		t.Fatalf("decode fetched book: %v", err)
	}
	doc["title"] = "The Go Programming Language (annotated)"
	edited, err := json.Marshal(doc)
	if err != nil {
		t.Fatalf("re-encode book: %v", err)
	}

	updated := ts.request(http.MethodPut, path, string(edited)).
		expect(t, http.StatusOK).book(t)
	if updated.Title != "The Go Programming Language (annotated)" {
		t.Errorf("title = %q, want the edited title", updated.Title)
	}
	if updated.ID != created.ID {
		t.Errorf("id = %d, want %d: the body's id must be ignored, not applied", updated.ID, created.ID)
	}
	if !updated.CreatedAt.Equal(created.CreatedAt) {
		t.Errorf("created_at = %v, want the stored %v: the body's value must be ignored",
			updated.CreatedAt, created.CreatedAt)
	}
}

func TestDeleteBookErrors(t *testing.T) {
	ts := newTestServer(t)

	created := ts.request(http.MethodPost, "/books", goBookJSON).
		expect(t, http.StatusCreated).book(t)
	path := "/books/" + itoa64(created.ID)

	ts.request(http.MethodDelete, path, "").expect(t, http.StatusNoContent)

	// Deleting twice is a 404, not a silent success.
	resp := ts.request(http.MethodDelete, path, "").expect(t, http.StatusNotFound)
	if code := resp.apiError(t).Code; code != "not_found" {
		t.Errorf("error code = %q, want \"not_found\"", code)
	}
}

func TestMethodNotAllowed(t *testing.T) {
	ts := newTestServer(t)

	tests := []struct {
		method    string
		path      string
		wantAllow string
	}{
		{http.MethodPatch, "/books", "GET, POST"},
		{http.MethodDelete, "/books", "GET, POST"},
		{http.MethodPut, "/books", "GET, POST"},
		{http.MethodPost, "/books/1", "GET, PUT, DELETE"},
		{http.MethodPatch, "/books/1", "GET, PUT, DELETE"},
		{http.MethodPost, "/health", "GET"},
	}

	for _, tt := range tests {
		resp := ts.request(tt.method, tt.path, "").expect(t, http.StatusMethodNotAllowed)
		if got := resp.header.Get("Allow"); got != tt.wantAllow {
			t.Errorf("%s %s Allow = %q, want %q", tt.method, tt.path, got, tt.wantAllow)
		}
		if code := resp.apiError(t).Code; code != "method_not_allowed" {
			t.Errorf("%s %s error code = %q, want \"method_not_allowed\"", tt.method, tt.path, code)
		}
	}
}

func TestUnknownRoutesReturnJSON(t *testing.T) {
	ts := newTestServer(t)

	// Includes the near-misses: a trailing slash is not a book id, and the
	// paths are case-sensitive.
	for _, path := range []string{"/", "/nope", "/books/1/reviews", "/BOOKS", "/books/", "/health/"} {
		resp := ts.request(http.MethodGet, path, "").expect(t, http.StatusNotFound)
		if code := resp.apiError(t).Code; code != "not_found" {
			t.Errorf("GET %s error code = %q, want \"not_found\"", path, code)
		}
	}
}

// When the database goes away, health must say so and the data endpoints must
// fail closed with an opaque 500 rather than leaking SQL detail.
func TestDatabaseUnavailable(t *testing.T) {
	ts := newTestServer(t)

	if err := ts.store.Close(); err != nil {
		t.Fatalf("Store.Close: %v", err)
	}

	resp := ts.request(http.MethodGet, "/health", "").expect(t, http.StatusServiceUnavailable)
	var health map[string]string
	if err := json.Unmarshal(resp.body, &health); err != nil {
		t.Fatalf("decode health body %s: %v", resp.body, err)
	}
	if health["status"] != "unavailable" || health["database"] != "unavailable" {
		t.Errorf("health body = %s, want both fields \"unavailable\"", resp.body)
	}

	for _, tt := range []struct{ method, path, body string }{
		{http.MethodGet, "/books", ""},
		{http.MethodGet, "/books/1", ""},
		{http.MethodPost, "/books", goBookJSON},
		{http.MethodPut, "/books/1", goBookJSON},
		{http.MethodDelete, "/books/1", ""},
	} {
		resp := ts.request(tt.method, tt.path, tt.body).expect(t, http.StatusInternalServerError)
		detail := resp.apiError(t)
		if detail.Code != "internal_error" {
			t.Errorf("%s %s error code = %q, want \"internal_error\"", tt.method, tt.path, detail.Code)
		}
		for _, leak := range []string{"sql", "sqlite", "SELECT", "books"} {
			if strings.Contains(detail.Message, leak) {
				t.Errorf("%s %s message %q leaks %q", tt.method, tt.path, detail.Message, leak)
			}
		}
	}
}

// A panic must not take the server down or leak a stack trace to the client.
func TestPanicIsRecovered(t *testing.T) {
	// A nil store panics on first use, which is exactly what the recovery
	// middleware exists to contain.
	srv := httptest.NewServer(NewAPI(nil, nil).Routes())
	defer srv.Close()

	resp, err := srv.Client().Get(srv.URL + "/health")
	if err != nil {
		t.Fatalf("GET /health: %v", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		t.Fatalf("read body: %v", err)
	}
	if resp.StatusCode != http.StatusInternalServerError {
		t.Fatalf("status = %d, want 500; body: %s", resp.StatusCode, body)
	}
	if bytes.Contains(body, []byte("goroutine")) || bytes.Contains(body, []byte(".go:")) {
		t.Errorf("response leaks internals: %s", body)
	}
}

func itoa64(id int64) string { return strconv.FormatInt(id, 10) }
