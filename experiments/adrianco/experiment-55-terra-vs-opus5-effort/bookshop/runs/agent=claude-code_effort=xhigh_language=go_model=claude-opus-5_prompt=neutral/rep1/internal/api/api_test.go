package api_test

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strings"
	"sync"
	"testing"
	"time"

	"bookapi/internal/api"
	"bookapi/internal/books"
)

// fixedNow pins the clock so the publication-year rule is deterministic.
var fixedNow = time.Date(2026, time.July, 29, 12, 0, 0, 0, time.UTC)

const jsonContentType = "application/json"

// newAPI returns a handler backed by an empty database in a temp directory.
func newAPI(t *testing.T) http.Handler {
	t.Helper()
	return api.NewServer(newStore(t), nil, api.WithClock(func() time.Time { return fixedNow }))
}

func newStore(t *testing.T) *books.Store {
	t.Helper()

	store, err := books.Open(t.Context(), filepath.Join(t.TempDir(), "books.db"))
	if err != nil {
		t.Fatalf("open store: %v", err)
	}
	t.Cleanup(func() { store.Close() })
	return store
}

// result is a captured HTTP response, with helpers for the assertions every
// test needs.
type result struct {
	t      *testing.T
	Status int
	Header http.Header
	Body   []byte
}

// send issues a request carrying a JSON content type. A nil body sends none; a
// string body is sent verbatim; anything else is marshalled.
func send(t *testing.T, h http.Handler, method, path string, body any) result {
	t.Helper()

	switch payload := body.(type) {
	case nil:
		return sendRaw(t, h, method, path, "", "")
	case string:
		return sendRaw(t, h, method, path, jsonContentType, payload)
	default:
		encoded, err := json.Marshal(payload)
		if err != nil {
			t.Fatalf("marshal request body: %v", err)
		}
		return sendRaw(t, h, method, path, jsonContentType, string(encoded))
	}
}

// sendRaw gives the caller full control over the content type and the bytes on
// the wire. An empty contentType omits the header entirely.
func sendRaw(t *testing.T, h http.Handler, method, path, contentType, body string) result {
	t.Helper()

	var reader io.Reader
	if body != "" {
		reader = strings.NewReader(body)
	}
	req := httptest.NewRequest(method, path, reader)
	if contentType != "" {
		req.Header.Set("Content-Type", contentType)
	}

	recorder := httptest.NewRecorder()
	h.ServeHTTP(recorder, req)
	response := recorder.Result()
	defer response.Body.Close()

	captured, err := io.ReadAll(response.Body)
	if err != nil {
		t.Fatalf("read response body: %v", err)
	}
	return result{t: t, Status: response.StatusCode, Header: response.Header, Body: captured}
}

// expect asserts the status code, dumping the body when it does not match
// so a failure explains itself.
func (r result) expect(status int) result {
	r.t.Helper()

	if r.Status != status {
		r.t.Fatalf("status = %d, want %d; body: %s", r.Status, status, r.Body)
	}
	return r
}

func (r result) decode(dst any) {
	r.t.Helper()

	if contentType := r.Header.Get("Content-Type"); !strings.HasPrefix(contentType, jsonContentType) {
		r.t.Fatalf("Content-Type = %q, want %s", contentType, jsonContentType)
	}
	if err := json.Unmarshal(r.Body, dst); err != nil {
		r.t.Fatalf("decode %T from %s: %v", dst, r.Body, err)
	}
}

func (r result) book() books.Book {
	r.t.Helper()

	var book books.Book
	r.decode(&book)
	return book
}

func (r result) apiError() api.ErrorResponse {
	r.t.Helper()

	var payload api.ErrorResponse
	r.decode(&payload)
	if payload.Error == "" {
		r.t.Errorf("error response %s has an empty error message", r.Body)
	}
	return payload
}

// createBook posts a book and asserts it was accepted.
func createBook(t *testing.T, h http.Handler, input books.Input) books.Book {
	t.Helper()
	return send(t, h, http.MethodPost, "/books", input).expect(http.StatusCreated).book()
}

// TestBookLifecycle walks a book through every endpoint in order, which is the
// closest thing to a smoke test for the whole API.
func TestBookLifecycle(t *testing.T) {
	t.Parallel()
	h := newAPI(t)

	// Create.
	input := books.Input{Title: "The Go Programming Language", Author: "Alan Donovan", Year: 2015, ISBN: "9780134190440"}
	created := send(t, h, http.MethodPost, "/books", input).expect(http.StatusCreated)

	book := created.book()
	if book.ID < 1 {
		t.Fatalf("created book has ID %d, want a positive integer", book.ID)
	}
	if book.Title != input.Title || book.Author != input.Author || book.Year != input.Year || book.ISBN != input.ISBN {
		t.Errorf("created book = %+v, want the fields of %+v", book, input)
	}
	location := fmt.Sprintf("/books/%d", book.ID)
	if got := created.Header.Get("Location"); got != location {
		t.Errorf("Location = %q, want %q", got, location)
	}

	// Read it back from the advertised location.
	fetched := send(t, h, http.MethodGet, location, nil).expect(http.StatusOK).book()
	if fetched != book {
		t.Errorf("GET %s = %+v, want %+v", location, fetched, book)
	}

	// List.
	var list struct {
		Books []books.Book `json:"books"`
		Count int          `json:"count"`
	}
	send(t, h, http.MethodGet, "/books", nil).expect(http.StatusOK).decode(&list)
	if list.Count != 1 || len(list.Books) != 1 || list.Books[0].ID != book.ID {
		t.Errorf("GET /books = %+v, want just book %d", list, book.ID)
	}

	// Update.
	revised := books.Input{Title: "The Go Programming Language, 2nd ed.", Author: "Alan A. A. Donovan", Year: 2016, ISBN: "9780134190440"}
	updated := send(t, h, http.MethodPut, location, revised).expect(http.StatusOK).book()
	if updated.ID != book.ID {
		t.Errorf("update changed the ID from %d to %d", book.ID, updated.ID)
	}
	if updated.Title != revised.Title || updated.Author != revised.Author || updated.Year != revised.Year {
		t.Errorf("updated book = %+v, want the fields of %+v", updated, revised)
	}
	if !updated.CreatedAt.Equal(book.CreatedAt) {
		t.Errorf("update changed created_at from %v to %v", book.CreatedAt, updated.CreatedAt)
	}

	// Delete.
	deleted := send(t, h, http.MethodDelete, location, nil).expect(http.StatusNoContent)
	if len(deleted.Body) != 0 {
		t.Errorf("DELETE returned a body of %q, want none with 204", deleted.Body)
	}

	// Gone.
	send(t, h, http.MethodGet, location, nil).expect(http.StatusNotFound).apiError()
	send(t, h, http.MethodDelete, location, nil).expect(http.StatusNotFound).apiError()
	send(t, h, http.MethodPut, location, revised).expect(http.StatusNotFound).apiError()

	send(t, h, http.MethodGet, "/books", nil).expect(http.StatusOK).decode(&list)
	if list.Count != 0 || len(list.Books) != 0 {
		t.Errorf("after delete GET /books = %+v, want empty", list)
	}
}

// TestListEncodesEmptyCollectionAsArray guards against the nil-slice-becomes-
// null trap, which breaks clients that iterate the result.
func TestListEncodesEmptyCollectionAsArray(t *testing.T) {
	t.Parallel()
	h := newAPI(t)

	body := string(send(t, h, http.MethodGet, "/books", nil).expect(http.StatusOK).Body)
	if !strings.Contains(body, `"books":[]`) {
		t.Errorf("empty list encoded as %s, want an empty JSON array", body)
	}
}

func TestCreateRejectsInvalidFields(t *testing.T) {
	t.Parallel()
	h := newAPI(t)

	tests := []struct {
		name       string
		body       string
		wantFields []string
	}{
		{
			name:       "missing title",
			body:       `{"author":"Anon"}`,
			wantFields: []string{"title"},
		},
		{
			name:       "blank title",
			body:       `{"title":"   ","author":"Anon"}`,
			wantFields: []string{"title"},
		},
		{
			name:       "missing author",
			body:       `{"title":"Untitled"}`,
			wantFields: []string{"author"},
		},
		{
			name:       "empty object reports both required fields",
			body:       `{}`,
			wantFields: []string{"title", "author"},
		},
		{
			name:       "year in the far future",
			body:       `{"title":"T","author":"A","year":3000}`,
			wantFields: []string{"year"},
		},
		{
			name:       "malformed isbn",
			body:       `{"title":"T","author":"A","isbn":"1234567890"}`,
			wantFields: []string{"isbn"},
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()

			payload := send(t, h, http.MethodPost, "/books", tc.body).
				expect(http.StatusUnprocessableEntity).
				apiError()

			if len(payload.Details) != len(tc.wantFields) {
				t.Fatalf("details = %v, want exactly the fields %v", payload.Details, tc.wantFields)
			}
			for _, field := range tc.wantFields {
				if _, ok := payload.Details[field]; !ok {
					t.Errorf("details %v has no entry for %q", payload.Details, field)
				}
			}
		})
	}
}

// TestValidationAppliesToUpdatesToo makes sure PUT is not a way around the
// rules POST enforces.
func TestValidationAppliesToUpdatesToo(t *testing.T) {
	t.Parallel()
	h := newAPI(t)

	book := createBook(t, h, books.Input{Title: "Valid", Author: "A"})
	path := fmt.Sprintf("/books/%d", book.ID)

	payload := send(t, h, http.MethodPut, path, `{"title":"","author":""}`).
		expect(http.StatusUnprocessableEntity).
		apiError()
	if _, ok := payload.Details["title"]; !ok {
		t.Errorf("details = %v, want a title entry", payload.Details)
	}

	// The rejected update must not have touched the stored book.
	unchanged := send(t, h, http.MethodGet, path, nil).expect(http.StatusOK).book()
	if unchanged.Title != "Valid" {
		t.Errorf("title = %q after a rejected update, want %q", unchanged.Title, "Valid")
	}
}

func TestCreateNormalizesInput(t *testing.T) {
	t.Parallel()
	h := newAPI(t)

	book := createBook(t, h, books.Input{
		Title:  "  Dune  ",
		Author: "\tFrank Herbert\n",
		Year:   1965,
		ISBN:   "978-0-441-01359-3",
	})

	if book.Title != "Dune" {
		t.Errorf("title = %q, want it trimmed to %q", book.Title, "Dune")
	}
	if book.Author != "Frank Herbert" {
		t.Errorf("author = %q, want it trimmed to %q", book.Author, "Frank Herbert")
	}
	if book.ISBN != "9780441013593" {
		t.Errorf("isbn = %q, want the hyphens stripped", book.ISBN)
	}
}

// TestOptionalFieldsAlwaysPresent keeps the response shape stable: a client
// reading book.year should not have to handle the key being absent.
func TestOptionalFieldsAlwaysPresent(t *testing.T) {
	t.Parallel()
	h := newAPI(t)

	body := send(t, h, http.MethodPost, "/books", `{"title":"T","author":"A"}`).
		expect(http.StatusCreated).Body

	var fields map[string]json.RawMessage
	if err := json.Unmarshal(body, &fields); err != nil {
		t.Fatalf("decode %s: %v", body, err)
	}
	for _, key := range []string{"id", "title", "author", "year", "isbn", "created_at", "updated_at"} {
		if _, ok := fields[key]; !ok {
			t.Errorf("response %s is missing the %q key", body, key)
		}
	}
}

func TestMalformedRequestsAreRejected(t *testing.T) {
	t.Parallel()
	h := newAPI(t)

	tests := []struct {
		name        string
		method      string
		path        string
		contentType string
		body        string
		wantStatus  int
	}{
		{
			name: "empty body", method: http.MethodPost, path: "/books",
			contentType: jsonContentType, body: "",
			wantStatus: http.StatusBadRequest,
		},
		{
			name: "truncated json", method: http.MethodPost, path: "/books",
			contentType: jsonContentType, body: `{"title":"T","author":`,
			wantStatus: http.StatusBadRequest,
		},
		{
			name: "not an object", method: http.MethodPost, path: "/books",
			contentType: jsonContentType, body: `["title"]`,
			wantStatus: http.StatusBadRequest,
		},
		{
			name: "wrong field type", method: http.MethodPost, path: "/books",
			contentType: jsonContentType, body: `{"title":42,"author":"A"}`,
			wantStatus: http.StatusBadRequest,
		},
		{
			name: "misspelled field", method: http.MethodPost, path: "/books",
			contentType: jsonContentType, body: `{"titel":"T","author":"A"}`,
			wantStatus: http.StatusBadRequest,
		},
		{
			name: "two objects in one body", method: http.MethodPost, path: "/books",
			contentType: jsonContentType, body: `{"title":"T","author":"A"}{"title":"U","author":"B"}`,
			wantStatus: http.StatusBadRequest,
		},
		{
			name: "missing content type", method: http.MethodPost, path: "/books",
			contentType: "", body: `{"title":"T","author":"A"}`,
			wantStatus: http.StatusUnsupportedMediaType,
		},
		{
			name: "form content type", method: http.MethodPost, path: "/books",
			contentType: "application/x-www-form-urlencoded", body: "title=T&author=A",
			wantStatus: http.StatusUnsupportedMediaType,
		},
		{
			name: "json content type with charset is fine", method: http.MethodPost, path: "/books",
			contentType: "application/json; charset=utf-8", body: `{"title":"T","author":"A"}`,
			wantStatus: http.StatusCreated,
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()

			got := sendRaw(t, h, tc.method, tc.path, tc.contentType, tc.body).expect(tc.wantStatus)
			if tc.wantStatus >= 400 {
				got.apiError()
			}
		})
	}
}

// TestOversizedBodyRejected checks the cap that keeps a hostile client from
// streaming an unbounded body into memory.
func TestOversizedBodyRejected(t *testing.T) {
	t.Parallel()
	h := newAPI(t)

	body := fmt.Sprintf(`{"title":%q,"author":"A"}`, strings.Repeat("x", 128<<10))
	sendRaw(t, h, http.MethodPost, "/books", jsonContentType, body).
		expect(http.StatusRequestEntityTooLarge).
		apiError()
}

func TestListFiltersByAuthor(t *testing.T) {
	t.Parallel()
	h := newAPI(t)

	donovan := createBook(t, h, books.Input{Title: "The Go Programming Language", Author: "Alan Donovan"})
	kernighan := createBook(t, h, books.Input{Title: "The Practice of Programming", Author: "Brian Kernighan"})

	tests := []struct {
		name    string
		query   string
		wantIDs []int64
	}{
		{name: "no filter returns everything", query: "", wantIDs: []int64{donovan.ID, kernighan.ID}},
		{name: "exact author", query: "?author=Alan+Donovan", wantIDs: []int64{donovan.ID}},
		{name: "case insensitive", query: "?author=alan+donovan", wantIDs: []int64{donovan.ID}},
		{name: "unknown author", query: "?author=Nobody", wantIDs: nil},
		{name: "empty author behaves as no filter", query: "?author=", wantIDs: []int64{donovan.ID, kernighan.ID}},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()

			var list struct {
				Books []books.Book `json:"books"`
				Count int          `json:"count"`
			}
			send(t, h, http.MethodGet, "/books"+tc.query, nil).expect(http.StatusOK).decode(&list)

			if list.Count != len(list.Books) {
				t.Errorf("count = %d but %d books were returned", list.Count, len(list.Books))
			}
			if len(list.Books) != len(tc.wantIDs) {
				t.Fatalf("GET /books%s returned %d books, want %d", tc.query, len(list.Books), len(tc.wantIDs))
			}
			for i, want := range tc.wantIDs {
				if list.Books[i].ID != want {
					t.Errorf("book %d has ID %d, want %d", i, list.Books[i].ID, want)
				}
			}
		})
	}
}

// TestListRejectsUnknownQueryParameter stops a typo in the filter name from
// silently returning the whole collection.
func TestListRejectsUnknownQueryParameter(t *testing.T) {
	t.Parallel()
	h := newAPI(t)

	send(t, h, http.MethodGet, "/books?auther=Donovan", nil).
		expect(http.StatusBadRequest).
		apiError()
}

func TestDuplicateISBNReturnsConflict(t *testing.T) {
	t.Parallel()
	h := newAPI(t)

	createBook(t, h, books.Input{Title: "Original", Author: "A", ISBN: "0306406152"})

	// Same ISBN, differently punctuated: the canonical form must still collide.
	send(t, h, http.MethodPost, "/books", books.Input{Title: "Reprint", Author: "B", ISBN: "0-306-40615-2"}).
		expect(http.StatusConflict).
		apiError()

	other := createBook(t, h, books.Input{Title: "Other", Author: "C", ISBN: "9780306406157"})
	send(t, h, http.MethodPut, fmt.Sprintf("/books/%d", other.ID),
		books.Input{Title: "Other", Author: "C", ISBN: "0306406152"}).
		expect(http.StatusConflict).
		apiError()

	// Books without an ISBN never collide with each other.
	createBook(t, h, books.Input{Title: "No ISBN", Author: "D"})
	createBook(t, h, books.Input{Title: "Also No ISBN", Author: "E"})
}

// TestUpdateReplacesWholeRecord documents PUT's replace-everything semantics.
func TestUpdateReplacesWholeRecord(t *testing.T) {
	t.Parallel()
	h := newAPI(t)

	book := createBook(t, h, books.Input{Title: "First", Author: "A", Year: 1999, ISBN: "0306406152"})
	path := fmt.Sprintf("/books/%d", book.ID)

	updated := send(t, h, http.MethodPut, path, `{"title":"Second","author":"B"}`).
		expect(http.StatusOK).
		book()

	if updated.Year != 0 || updated.ISBN != "" {
		t.Errorf("PUT left year %d and isbn %q, want them cleared: PUT replaces the record",
			updated.Year, updated.ISBN)
	}
}

func TestRoutingAndMethodErrors(t *testing.T) {
	t.Parallel()
	h := newAPI(t)

	book := createBook(t, h, books.Input{Title: "T", Author: "A"})

	t.Run("non-numeric id is a bad request", func(t *testing.T) {
		t.Parallel()
		// Includes an escaped space and a value past the range of an int64.
		for _, id := range []string{"abc", "1.5", "1e3", "-3", "0", "%20", "9223372036854775808"} {
			send(t, h, http.MethodGet, "/books/"+id, nil).
				expect(http.StatusBadRequest).
				apiError()
		}
	})

	t.Run("unknown id is a not found", func(t *testing.T) {
		t.Parallel()
		send(t, h, http.MethodGet, "/books/999999", nil).
			expect(http.StatusNotFound).
			apiError()
	})

	t.Run("unknown route is a not found", func(t *testing.T) {
		t.Parallel()
		for _, path := range []string{"/", "/authors", "/books/1/reviews"} {
			send(t, h, http.MethodGet, path, nil).
				expect(http.StatusNotFound).
				apiError()
		}
	})

	t.Run("wrong method advertises what is allowed", func(t *testing.T) {
		t.Parallel()

		tests := []struct {
			method    string
			path      string
			wantAllow string
		}{
			{method: http.MethodDelete, path: "/books", wantAllow: "GET, POST"},
			{method: http.MethodPut, path: "/books", wantAllow: "GET, POST"},
			{method: http.MethodPatch, path: fmt.Sprintf("/books/%d", book.ID), wantAllow: "GET, PUT, DELETE"},
			{method: http.MethodPost, path: fmt.Sprintf("/books/%d", book.ID), wantAllow: "GET, PUT, DELETE"},
			{method: http.MethodPost, path: "/health", wantAllow: "GET"},
		}
		for _, tc := range tests {
			got := sendRaw(t, h, tc.method, tc.path, jsonContentType, `{"title":"T","author":"A"}`).
				expect(http.StatusMethodNotAllowed)
			got.apiError()
			if allow := got.Header.Get("Allow"); allow != tc.wantAllow {
				t.Errorf("%s %s: Allow = %q, want %q", tc.method, tc.path, allow, tc.wantAllow)
			}
		}
	})
}

func TestHealthReportsReady(t *testing.T) {
	t.Parallel()
	h := newAPI(t)

	var payload struct {
		Status   string `json:"status"`
		Database string `json:"database"`
	}
	send(t, h, http.MethodGet, "/health", nil).expect(http.StatusOK).decode(&payload)

	if payload.Status != "ok" || payload.Database != "ok" {
		t.Errorf("health = %+v, want both fields ok", payload)
	}
}

// TestHealthReportsDatabaseFailure checks that /health actually depends on the
// database rather than always answering "ok".
func TestHealthReportsDatabaseFailure(t *testing.T) {
	t.Parallel()

	store := newStore(t)
	h := api.NewServer(store, nil)
	if err := store.Close(); err != nil {
		t.Fatalf("close store: %v", err)
	}

	var payload struct {
		Status   string `json:"status"`
		Database string `json:"database"`
	}
	send(t, h, http.MethodGet, "/health", nil).expect(http.StatusServiceUnavailable).decode(&payload)

	if payload.Status == "ok" {
		t.Errorf("health = %+v with a closed database, want a degraded status", payload)
	}
}

// TestConcurrentCreates runs the handler from many goroutines at once: every
// request must succeed and every book must get its own ID.
func TestConcurrentCreates(t *testing.T) {
	t.Parallel()
	h := newAPI(t)

	const clients = 20

	var (
		wg  sync.WaitGroup
		mu  sync.Mutex
		ids = make(map[int64]bool, clients)
	)
	for i := range clients {
		wg.Add(1)
		go func() {
			defer wg.Done()

			book := createBook(t, h, books.Input{Title: fmt.Sprintf("Book %d", i), Author: "A"})
			mu.Lock()
			defer mu.Unlock()
			ids[book.ID] = true
		}()
	}
	wg.Wait()

	if len(ids) != clients {
		t.Errorf("%d concurrent creates produced %d distinct IDs", clients, len(ids))
	}
}

// TestHeadRequestsReportContentLength covers a subtlety of ServeMux: a
// "GET /books" pattern also serves HEAD. The handler must write its body as
// usual and let net/http discard it, which is what produces a Content-Length
// matching the GET response instead of a bare zero.
func TestHeadRequestsReportContentLength(t *testing.T) {
	t.Parallel()

	h := newAPI(t)
	createBook(t, h, books.Input{Title: "Measured", Author: "A"})

	server := httptest.NewServer(h)
	defer server.Close()

	for _, path := range []string{"/health", "/books", "/books/1"} {
		getResp, err := server.Client().Get(server.URL + path)
		if err != nil {
			t.Fatalf("GET %s: %v", path, err)
		}
		body, _ := io.ReadAll(getResp.Body)
		getResp.Body.Close()

		req, err := http.NewRequest(http.MethodHead, server.URL+path, nil)
		if err != nil {
			t.Fatalf("build HEAD %s: %v", path, err)
		}
		headResp, err := server.Client().Do(req)
		if err != nil {
			t.Fatalf("HEAD %s: %v", path, err)
		}
		headResp.Body.Close()

		if headResp.StatusCode != getResp.StatusCode {
			t.Errorf("HEAD %s = %d, want %d like GET", path, headResp.StatusCode, getResp.StatusCode)
		}
		if headResp.ContentLength != int64(len(body)) {
			t.Errorf("HEAD %s reported Content-Length %d, want %d to match the GET body",
				path, headResp.ContentLength, len(body))
		}
	}
}

// TestOverRealHTTPServer repeats the core flow against a real listener, so the
// routing is proven against net/http rather than only against a recorder.
func TestOverRealHTTPServer(t *testing.T) {
	t.Parallel()

	server := httptest.NewServer(newAPI(t))
	defer server.Close()

	client := server.Client()

	resp, err := client.Post(server.URL+"/books", jsonContentType,
		strings.NewReader(`{"title":"Networked","author":"A. Author","year":2020}`))
	if err != nil {
		t.Fatalf("POST /books: %v", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusCreated {
		body, _ := io.ReadAll(resp.Body)
		t.Fatalf("POST /books = %d, want 201; body: %s", resp.StatusCode, body)
	}

	var created books.Book
	if err := json.NewDecoder(resp.Body).Decode(&created); err != nil {
		t.Fatalf("decode created book: %v", err)
	}

	getResp, err := client.Get(fmt.Sprintf("%s/books/%d", server.URL, created.ID))
	if err != nil {
		t.Fatalf("GET /books/%d: %v", created.ID, err)
	}
	defer getResp.Body.Close()
	if getResp.StatusCode != http.StatusOK {
		t.Fatalf("GET /books/%d = %d, want 200", created.ID, getResp.StatusCode)
	}

	var fetched books.Book
	if err := json.NewDecoder(getResp.Body).Decode(&fetched); err != nil {
		t.Fatalf("decode fetched book: %v", err)
	}
	if fetched.ID != created.ID || fetched.Title != "Networked" {
		t.Errorf("fetched %+v, want the book just created (%+v)", fetched, created)
	}

	healthResp, err := client.Get(server.URL + "/health")
	if err != nil {
		t.Fatalf("GET /health: %v", err)
	}
	defer healthResp.Body.Close()
	if healthResp.StatusCode != http.StatusOK {
		t.Errorf("GET /health = %d, want 200", healthResp.StatusCode)
	}
}
