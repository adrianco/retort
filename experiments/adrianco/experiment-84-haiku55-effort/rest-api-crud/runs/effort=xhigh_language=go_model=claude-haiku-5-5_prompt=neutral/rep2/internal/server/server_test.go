package server

import (
	"encoding/json"
	"io"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strconv"
	"strings"
	"testing"

	"bookapi/internal/book"
	"bookapi/internal/store"
)

// testAPI bundles the handler under test with the store behind it so tests
// can close the database to simulate failures.
type testAPI struct {
	handler http.Handler
	store   *store.Store
}

func newTestAPI(t *testing.T) testAPI {
	t.Helper()
	st, err := store.Open(filepath.Join(t.TempDir(), "books.db"))
	if err != nil {
		t.Fatalf("store.Open() error = %v", err)
	}
	t.Cleanup(func() { st.Close() })

	logger := slog.New(slog.NewTextHandler(io.Discard, nil))
	return testAPI{handler: New(st, logger).Handler(), store: st}
}

func (a testAPI) do(method, target, body string) *httptest.ResponseRecorder {
	req := httptest.NewRequest(method, target, strings.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	a.handler.ServeHTTP(rec, req)
	return rec
}

// create posts a book and fails the test unless the API returns 201.
func (a testAPI) create(t *testing.T, body string) book.Book {
	t.Helper()
	rec := a.do(http.MethodPost, "/books", body)
	if rec.Code != http.StatusCreated {
		t.Fatalf("POST /books status = %d, body = %s", rec.Code, rec.Body)
	}
	return decodeResponse[book.Book](t, rec)
}

func decodeResponse[T any](t *testing.T, rec *httptest.ResponseRecorder) T {
	t.Helper()
	var v T
	if err := json.Unmarshal(rec.Body.Bytes(), &v); err != nil {
		t.Fatalf("decode response %q: %v", rec.Body.String(), err)
	}
	return v
}

func assertStatus(t *testing.T, rec *httptest.ResponseRecorder, want int) {
	t.Helper()
	if rec.Code != want {
		t.Fatalf("status = %d, want %d; body = %s", rec.Code, want, rec.Body)
	}
}

func assertJSONError(t *testing.T, rec *httptest.ResponseRecorder, wantMsg string) errorBody {
	t.Helper()
	if ct := rec.Header().Get("Content-Type"); ct != "application/json" {
		t.Errorf("error Content-Type = %q, want application/json", ct)
	}
	body := decodeResponse[errorBody](t, rec)
	if body.Error != wantMsg {
		t.Errorf("error message = %q, want %q", body.Error, wantMsg)
	}
	return body
}

func TestBookLifecycle(t *testing.T) {
	api := newTestAPI(t)

	created := api.create(t, `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0-441-01359-3"}`)
	if created.ID == 0 {
		t.Fatal("created book has no ID")
	}
	if created.ISBN == nil || *created.ISBN != "9780441013593" {
		t.Errorf("ISBN = %v, want normalized 9780441013593", created.ISBN)
	}

	// The 201 response carries a Location header pointing at the new resource.
	post := api.do(http.MethodPost, "/books", `{"title":"Emma","author":"Jane Austen"}`)
	if loc, want := post.Header().Get("Location"), "/books/"+itoa(created.ID+1); loc != want {
		t.Errorf("Location = %q, want %q", loc, want)
	}

	get := api.do(http.MethodGet, "/books/"+itoa(created.ID), "")
	assertStatus(t, get, http.StatusOK)
	if got := decodeResponse[book.Book](t, get); got.Title != "Dune" || got.Year == nil || *got.Year != 1965 {
		t.Errorf("GET returned %+v, want Dune/1965", got)
	}

	put := api.do(http.MethodPut, "/books/"+itoa(created.ID), `{"title":"Dune Messiah","author":"Frank Herbert"}`)
	assertStatus(t, put, http.StatusOK)
	updated := decodeResponse[book.Book](t, put)
	if updated.Title != "Dune Messiah" || updated.Year != nil || updated.ISBN != nil {
		t.Errorf("PUT returned %+v, want Dune Messiah with year and isbn cleared", updated)
	}

	list := api.do(http.MethodGet, "/books", "")
	assertStatus(t, list, http.StatusOK)
	if books := decodeResponse[[]book.Book](t, list); len(books) != 2 {
		t.Errorf("GET /books returned %d books, want 2", len(books))
	}

	del := api.do(http.MethodDelete, "/books/"+itoa(created.ID), "")
	assertStatus(t, del, http.StatusNoContent)
	if del.Body.Len() != 0 {
		t.Errorf("DELETE body = %q, want empty", del.Body)
	}

	assertStatus(t, api.do(http.MethodGet, "/books/"+itoa(created.ID), ""), http.StatusNotFound)
}

func TestCreateValidation(t *testing.T) {
	api := newTestAPI(t)

	tests := []struct {
		name   string
		body   string
		fields []string
	}{
		{"missing title", `{"author":"Frank Herbert"}`, []string{"title"}},
		{"missing author", `{"title":"Dune"}`, []string{"author"}},
		{"blank title and author", `{"title":"   ","author":""}`, []string{"title", "author"}},
		{"invalid ISBN", `{"title":"t","author":"a","isbn":"123"}`, []string{"isbn"}},
		{"ISBN checksum wrong", `{"title":"t","author":"a","isbn":"0306406153"}`, []string{"isbn"}},
		{"year in the far future", `{"title":"t","author":"a","year":9999}`, []string{"year"}},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			rec := api.do(http.MethodPost, "/books", tt.body)
			assertStatus(t, rec, http.StatusBadRequest)
			body := assertJSONError(t, rec, "validation failed")
			for _, f := range tt.fields {
				if _, ok := body.Details[f]; !ok {
					t.Errorf("details = %v, want an entry for %q", body.Details, f)
				}
			}
		})
	}

	// Nothing should have been stored by the rejected requests.
	list := api.do(http.MethodGet, "/books", "")
	assertStatus(t, list, http.StatusOK)
	if books := decodeResponse[[]book.Book](t, list); len(books) != 0 {
		t.Errorf("rejected creates left %d books behind", len(books))
	}
}

func TestMalformedBodiesAreRejected(t *testing.T) {
	api := newTestAPI(t)

	tests := []struct {
		name string
		body string
	}{
		{"empty body", ``},
		{"not JSON", `title=Dune`},
		{"unknown field", `{"title":"t","author":"a","pages":300}`},
		{"wrong type for year", `{"title":"t","author":"a","year":"1965"}`},
		{"two objects", `{"title":"t","author":"a"}{"title":"u","author":"b"}`},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			assertStatus(t, api.do(http.MethodPost, "/books", tt.body), http.StatusBadRequest)
		})
	}
}

func TestOversizedBodyReturns413(t *testing.T) {
	api := newTestAPI(t)

	huge := `{"title":"` + strings.Repeat("a", maxBodyBytes) + `","author":"a"}`
	assertStatus(t, api.do(http.MethodPost, "/books", huge), http.StatusRequestEntityTooLarge)
}

func TestListFiltersByAuthor(t *testing.T) {
	api := newTestAPI(t)
	api.create(t, `{"title":"Dune","author":"Frank Herbert"}`)
	api.create(t, `{"title":"Emma","author":"Jane Austen"}`)
	api.create(t, `{"title":"Children of Dune","author":"Frank Herbert"}`)

	tests := []struct {
		name   string
		target string
		want   int
	}{
		{"no filter", "/books", 3},
		{"exact author", "/books?author=Frank+Herbert", 2},
		{"case-insensitive author", "/books?author=jane%20austen", 1},
		{"blank author is ignored", "/books?author=", 3},
		{"no matches", "/books?author=Nobody", 0},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			rec := api.do(http.MethodGet, tt.target, "")
			assertStatus(t, rec, http.StatusOK)
			if got := len(decodeResponse[[]book.Book](t, rec)); got != tt.want {
				t.Errorf("GET %s returned %d books, want %d", tt.target, got, tt.want)
			}
		})
	}

	// An empty result is an empty JSON array, not null.
	if body := strings.TrimSpace(api.do(http.MethodGet, "/books?author=Nobody", "").Body.String()); body != "[]" {
		t.Errorf("empty list body = %s, want []", body)
	}
}

func TestMissingBookReturns404(t *testing.T) {
	api := newTestAPI(t)
	const path = "/books/999"
	valid := `{"title":"t","author":"a"}`

	assertJSONError(t, api.do(http.MethodGet, path, ""), "book not found")
	assertJSONError(t, api.do(http.MethodPut, path, valid), "book not found")
	assertJSONError(t, api.do(http.MethodDelete, path, ""), "book not found")
}

func TestNonIntegerIDReturns400(t *testing.T) {
	api := newTestAPI(t)

	for _, method := range []string{http.MethodGet, http.MethodPut, http.MethodDelete} {
		rec := api.do(method, "/books/abc", `{"title":"t","author":"a"}`)
		assertStatus(t, rec, http.StatusBadRequest)
		assertJSONError(t, rec, "id must be an integer")
	}
}

func TestUpdateValidationLeavesBookUnchanged(t *testing.T) {
	api := newTestAPI(t)
	created := api.create(t, `{"title":"Original","author":"Author"}`)

	rec := api.do(http.MethodPut, "/books/"+itoa(created.ID), `{"title":"Changed"}`)
	assertStatus(t, rec, http.StatusBadRequest)
	assertJSONError(t, rec, "validation failed")

	got := decodeResponse[book.Book](t, api.do(http.MethodGet, "/books/"+itoa(created.ID), ""))
	if got.Title != "Original" {
		t.Errorf("title after failed PUT = %q, want Original", got.Title)
	}
}

func TestHealthReportsDatabaseStatus(t *testing.T) {
	api := newTestAPI(t)

	rec := api.do(http.MethodGet, "/health", "")
	assertStatus(t, rec, http.StatusOK)
	if status := decodeResponse[map[string]string](t, rec)["status"]; status != "ok" {
		t.Errorf("health status = %q, want ok", status)
	}

	// With the database gone, health must report the service as unavailable.
	if err := api.store.Close(); err != nil {
		t.Fatalf("Close() error = %v", err)
	}
	rec = api.do(http.MethodGet, "/health", "")
	assertStatus(t, rec, http.StatusServiceUnavailable)
	if status := decodeResponse[map[string]string](t, rec)["status"]; status != "unavailable" {
		t.Errorf("health status = %q, want unavailable", status)
	}
}

func TestUnsupportedMethodsAndRoutes(t *testing.T) {
	api := newTestAPI(t)

	tests := []struct {
		name      string
		method    string
		target    string
		wantCode  int
		wantMsg   string
		wantAllow string
	}{
		{"delete collection", http.MethodDelete, "/books", http.StatusMethodNotAllowed, "method not allowed", "GET, POST"},
		{"post to book", http.MethodPost, "/books/1", http.StatusMethodNotAllowed, "method not allowed", "GET, PUT, DELETE"},
		{"post to health", http.MethodPost, "/health", http.StatusMethodNotAllowed, "method not allowed", "GET"},
		{"unknown path", http.MethodGet, "/nope", http.StatusNotFound, "route not found", ""},
		{"extra path segment", http.MethodGet, "/books/1/extra", http.StatusNotFound, "route not found", ""},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			rec := api.do(tt.method, tt.target, "")
			assertStatus(t, rec, tt.wantCode)
			if got := rec.Header().Get("Allow"); got != tt.wantAllow {
				t.Errorf("Allow = %q, want %q", got, tt.wantAllow)
			}
			assertJSONError(t, rec, tt.wantMsg)
		})
	}
}

func itoa(n int64) string {
	return strconv.FormatInt(n, 10)
}
