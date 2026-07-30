package main

import (
	"bytes"
	"encoding/json"
	"io"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"strconv"
	"strings"
	"testing"
)

// newTestAPI spins up the full stack (router + real SQLite store) against an
// in-memory database, so these are integration tests over the HTTP surface.
func newTestAPI(t *testing.T) http.Handler {
	t.Helper()

	store, err := OpenStore(":memory:")
	if err != nil {
		t.Fatalf("OpenStore: %v", err)
	}
	t.Cleanup(func() {
		if err := store.Close(); err != nil {
			t.Errorf("Close: %v", err)
		}
	})

	// Discard log output so failing-path tests stay quiet.
	log := slog.New(slog.NewTextHandler(io.Discard, nil))
	return NewAPI(store, log)
}

// do issues a request against the handler. A nil body sends no body at all.
func do(t *testing.T, h http.Handler, method, target string, body any) *httptest.ResponseRecorder {
	t.Helper()

	var reader io.Reader
	if body != nil {
		switch v := body.(type) {
		case string: // raw payload, used for malformed-JSON cases
			reader = strings.NewReader(v)
		default:
			encoded, err := json.Marshal(v)
			if err != nil {
				t.Fatalf("marshal body: %v", err)
			}
			reader = bytes.NewReader(encoded)
		}
	}

	req := httptest.NewRequest(method, target, reader)
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

func decodeBook(t *testing.T, rec *httptest.ResponseRecorder) Book {
	t.Helper()
	var b Book
	if err := json.Unmarshal(rec.Body.Bytes(), &b); err != nil {
		t.Fatalf("decode book: %v (body=%s)", err, rec.Body)
	}
	return b
}

func decodeError(t *testing.T, rec *httptest.ResponseRecorder) errorBody {
	t.Helper()
	var e errorBody
	if err := json.Unmarshal(rec.Body.Bytes(), &e); err != nil {
		t.Fatalf("decode error: %v (body=%s)", err, rec.Body)
	}
	return e
}

func checkStatus(t *testing.T, rec *httptest.ResponseRecorder, want int) {
	t.Helper()
	if rec.Code != want {
		t.Fatalf("status = %d, want %d (body=%s)", rec.Code, want, rec.Body)
	}
	if ct := rec.Header().Get("Content-Type"); want != http.StatusNoContent && !strings.HasPrefix(ct, "application/json") {
		t.Errorf("Content-Type = %q, want application/json", ct)
	}
}

// createBook is a helper for tests that need a book to already exist.
func createBook(t *testing.T, h http.Handler, in BookInput) Book {
	t.Helper()
	rec := do(t, h, http.MethodPost, "/books", in)
	checkStatus(t, rec, http.StatusCreated)
	return decodeBook(t, rec)
}

func TestHealth(t *testing.T) {
	h := newTestAPI(t)

	rec := do(t, h, http.MethodGet, "/health", nil)
	checkStatus(t, rec, http.StatusOK)

	var body map[string]string
	if err := json.Unmarshal(rec.Body.Bytes(), &body); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if body["status"] != "ok" || body["database"] != "up" {
		t.Errorf("health body = %v, want status=ok database=up", body)
	}
}

func TestCreateBook(t *testing.T) {
	h := newTestAPI(t)

	rec := do(t, h, http.MethodPost, "/books", BookInput{
		Title:  "  The Go Programming Language  ",
		Author: "Alan Donovan",
		Year:   2015,
		ISBN:   "978-0-13-419044-0",
	})
	checkStatus(t, rec, http.StatusCreated)

	got := decodeBook(t, rec)
	if got.ID <= 0 {
		t.Errorf("ID = %d, want a positive generated id", got.ID)
	}
	if got.Title != "The Go Programming Language" {
		t.Errorf("Title = %q, want surrounding whitespace trimmed", got.Title)
	}
	if got.ISBN != "9780134190440" {
		t.Errorf("ISBN = %q, want hyphens normalized away", got.ISBN)
	}
	if got.Year != 2015 || got.Author != "Alan Donovan" {
		t.Errorf("got %+v, want year 2015 and author Alan Donovan", got)
	}
	if got.CreatedAt == "" || got.UpdatedAt == "" {
		t.Errorf("timestamps = %q/%q, want both populated", got.CreatedAt, got.UpdatedAt)
	}
	if loc := rec.Header().Get("Location"); loc == "" {
		t.Error("Location header is missing")
	}

	// The book must be readable afterwards, proving it reached the database.
	rec = do(t, h, http.MethodGet, "/books/"+itoa(got.ID), nil)
	checkStatus(t, rec, http.StatusOK)
	if fetched := decodeBook(t, rec); fetched != got {
		t.Errorf("fetched = %+v, want %+v", fetched, got)
	}
}

func TestCreateBookValidation(t *testing.T) {
	h := newTestAPI(t)

	tests := []struct {
		name       string
		body       any
		wantStatus int
		wantField  string
	}{
		{
			name:       "missing title",
			body:       BookInput{Author: "Ursula K. Le Guin"},
			wantStatus: http.StatusUnprocessableEntity,
			wantField:  "title",
		},
		{
			name:       "blank title",
			body:       BookInput{Title: "   ", Author: "Ursula K. Le Guin"},
			wantStatus: http.StatusUnprocessableEntity,
			wantField:  "title",
		},
		{
			name:       "missing author",
			body:       BookInput{Title: "The Dispossessed"},
			wantStatus: http.StatusUnprocessableEntity,
			wantField:  "author",
		},
		{
			name:       "implausible year",
			body:       BookInput{Title: "A", Author: "B", Year: 12000},
			wantStatus: http.StatusUnprocessableEntity,
			wantField:  "year",
		},
		{
			name:       "bad isbn check digit",
			body:       BookInput{Title: "A", Author: "B", ISBN: "978-0-13-419044-1"},
			wantStatus: http.StatusUnprocessableEntity,
			wantField:  "isbn",
		},
		{
			name:       "malformed json",
			body:       `{"title": "A", `,
			wantStatus: http.StatusBadRequest,
		},
		{
			name:       "unknown field",
			body:       `{"title":"A","author":"B","publisher":"C"}`,
			wantStatus: http.StatusBadRequest,
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			rec := do(t, h, http.MethodPost, "/books", tc.body)
			checkStatus(t, rec, tc.wantStatus)

			body := decodeError(t, rec)
			if body.Error == "" {
				t.Error("error message is empty")
			}
			if tc.wantField != "" {
				if _, ok := body.Fields[tc.wantField]; !ok {
					t.Errorf("fields = %v, want an entry for %q", body.Fields, tc.wantField)
				}
			}
		})
	}

	// A rejected request must not have written anything.
	rec := do(t, h, http.MethodGet, "/books", nil)
	checkStatus(t, rec, http.StatusOK)
	if count := decodeList(t, rec).Count; count != 0 {
		t.Errorf("count = %d, want 0 after only invalid creates", count)
	}
}

type listResponse struct {
	Books []Book `json:"books"`
	Count int    `json:"count"`
}

func decodeList(t *testing.T, rec *httptest.ResponseRecorder) listResponse {
	t.Helper()
	var l listResponse
	if err := json.Unmarshal(rec.Body.Bytes(), &l); err != nil {
		t.Fatalf("decode list: %v (body=%s)", err, rec.Body)
	}
	return l
}

func TestListBooksAndAuthorFilter(t *testing.T) {
	h := newTestAPI(t)

	createBook(t, h, BookInput{Title: "A Wizard of Earthsea", Author: "Ursula K. Le Guin", Year: 1968})
	createBook(t, h, BookInput{Title: "The Dispossessed", Author: "Ursula K. Le Guin", Year: 1974})
	createBook(t, h, BookInput{Title: "Dune", Author: "Frank Herbert", Year: 1965})

	t.Run("all", func(t *testing.T) {
		rec := do(t, h, http.MethodGet, "/books", nil)
		checkStatus(t, rec, http.StatusOK)

		list := decodeList(t, rec)
		if list.Count != 3 || len(list.Books) != 3 {
			t.Fatalf("count = %d, len = %d, want 3 and 3", list.Count, len(list.Books))
		}
		// Results are ordered by id, i.e. insertion order.
		if list.Books[0].Title != "A Wizard of Earthsea" || list.Books[2].Title != "Dune" {
			t.Errorf("unexpected order: %q ... %q", list.Books[0].Title, list.Books[2].Title)
		}
	})

	t.Run("filter by author", func(t *testing.T) {
		rec := do(t, h, http.MethodGet, "/books?author=Frank+Herbert", nil)
		checkStatus(t, rec, http.StatusOK)

		list := decodeList(t, rec)
		if list.Count != 1 {
			t.Fatalf("count = %d, want 1 (body=%s)", list.Count, rec.Body)
		}
		if list.Books[0].Title != "Dune" {
			t.Errorf("title = %q, want Dune", list.Books[0].Title)
		}
	})

	t.Run("filter is case-insensitive", func(t *testing.T) {
		rec := do(t, h, http.MethodGet, "/books?author=ursula+k.+le+guin", nil)
		checkStatus(t, rec, http.StatusOK)

		if list := decodeList(t, rec); list.Count != 2 {
			t.Errorf("count = %d, want 2", list.Count)
		}
	})

	t.Run("filter with no matches returns empty array", func(t *testing.T) {
		rec := do(t, h, http.MethodGet, "/books?author=Nobody", nil)
		checkStatus(t, rec, http.StatusOK)

		if list := decodeList(t, rec); list.Count != 0 || list.Books == nil {
			t.Errorf("got count=%d books=%v, want 0 and a non-null empty array", list.Count, list.Books)
		}
		if !strings.Contains(rec.Body.String(), `"books":[]`) {
			t.Errorf("body = %s, want books serialized as [] not null", rec.Body)
		}
	})
}

func TestGetBookNotFound(t *testing.T) {
	h := newTestAPI(t)

	rec := do(t, h, http.MethodGet, "/books/999", nil)
	checkStatus(t, rec, http.StatusNotFound)

	rec = do(t, h, http.MethodGet, "/books/not-a-number", nil)
	checkStatus(t, rec, http.StatusBadRequest)
}

func TestUpdateBook(t *testing.T) {
	h := newTestAPI(t)
	created := createBook(t, h, BookInput{Title: "Old Title", Author: "Old Author", Year: 1990, ISBN: "0306406152"})

	rec := do(t, h, http.MethodPut, "/books/"+itoa(created.ID), BookInput{
		Title:  "New Title",
		Author: "New Author",
		Year:   2001,
	})
	checkStatus(t, rec, http.StatusOK)

	updated := decodeBook(t, rec)
	if updated.ID != created.ID {
		t.Errorf("ID = %d, want %d unchanged", updated.ID, created.ID)
	}
	if updated.Title != "New Title" || updated.Author != "New Author" || updated.Year != 2001 {
		t.Errorf("got %+v, want the new title/author/year", updated)
	}
	if updated.ISBN != "" {
		t.Errorf("ISBN = %q, want PUT to clear omitted fields", updated.ISBN)
	}
	if updated.CreatedAt != created.CreatedAt {
		t.Errorf("CreatedAt = %q, want it preserved as %q", updated.CreatedAt, created.CreatedAt)
	}

	// The change must be durable, not just reflected in the response.
	rec = do(t, h, http.MethodGet, "/books/"+itoa(created.ID), nil)
	checkStatus(t, rec, http.StatusOK)
	if got := decodeBook(t, rec); got.Title != "New Title" {
		t.Errorf("re-fetched title = %q, want New Title", got.Title)
	}

	t.Run("unknown id", func(t *testing.T) {
		rec := do(t, h, http.MethodPut, "/books/4242", BookInput{Title: "T", Author: "A"})
		checkStatus(t, rec, http.StatusNotFound)
	})

	t.Run("validation still applies", func(t *testing.T) {
		rec := do(t, h, http.MethodPut, "/books/"+itoa(created.ID), BookInput{Author: "A"})
		checkStatus(t, rec, http.StatusUnprocessableEntity)
	})
}

func TestDeleteBook(t *testing.T) {
	h := newTestAPI(t)
	created := createBook(t, h, BookInput{Title: "Ephemeral", Author: "Someone"})

	rec := do(t, h, http.MethodDelete, "/books/"+itoa(created.ID), nil)
	if rec.Code != http.StatusNoContent {
		t.Fatalf("status = %d, want 204 (body=%s)", rec.Code, rec.Body)
	}
	if rec.Body.Len() != 0 {
		t.Errorf("body = %q, want empty for 204", rec.Body)
	}

	rec = do(t, h, http.MethodGet, "/books/"+itoa(created.ID), nil)
	checkStatus(t, rec, http.StatusNotFound)

	// Deleting again is a 404, not a silent success.
	rec = do(t, h, http.MethodDelete, "/books/"+itoa(created.ID), nil)
	checkStatus(t, rec, http.StatusNotFound)
}

func TestDuplicateISBNConflicts(t *testing.T) {
	h := newTestAPI(t)
	createBook(t, h, BookInput{Title: "First", Author: "A", ISBN: "0306406152"})

	rec := do(t, h, http.MethodPost, "/books", BookInput{Title: "Second", Author: "B", ISBN: "0-306-40615-2"})
	checkStatus(t, rec, http.StatusConflict)

	// A blank ISBN is exempt from the uniqueness rule.
	createBook(t, h, BookInput{Title: "Third", Author: "C"})
	createBook(t, h, BookInput{Title: "Fourth", Author: "D"})
}

func TestMethodAndRouteHandling(t *testing.T) {
	h := newTestAPI(t)

	t.Run("unknown path", func(t *testing.T) {
		rec := do(t, h, http.MethodGet, "/authors", nil)
		checkStatus(t, rec, http.StatusNotFound)
	})

	t.Run("unsupported method", func(t *testing.T) {
		rec := do(t, h, http.MethodPatch, "/books/1", nil)
		if rec.Code != http.StatusMethodNotAllowed {
			t.Errorf("status = %d, want 405", rec.Code)
		}
	})

	t.Run("wrong content type", func(t *testing.T) {
		req := httptest.NewRequest(http.MethodPost, "/books", strings.NewReader("title=A"))
		req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
		rec := httptest.NewRecorder()
		h.ServeHTTP(rec, req)
		checkStatus(t, rec, http.StatusUnsupportedMediaType)
	})

	t.Run("empty body", func(t *testing.T) {
		req := httptest.NewRequest(http.MethodPost, "/books", nil)
		req.Header.Set("Content-Type", "application/json")
		rec := httptest.NewRecorder()
		h.ServeHTTP(rec, req)
		checkStatus(t, rec, http.StatusBadRequest)
	})
}

func itoa(id int64) string { return strconv.FormatInt(id, 10) }
