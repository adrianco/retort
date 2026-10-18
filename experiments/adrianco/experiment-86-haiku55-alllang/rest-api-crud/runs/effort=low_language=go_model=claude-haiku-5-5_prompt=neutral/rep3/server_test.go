package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strconv"
	"strings"
	"testing"
)

func newTestServer(t *testing.T) *Server {
	t.Helper()
	store, err := OpenStore(":memory:")
	if err != nil {
		t.Fatalf("open store: %v", err)
	}
	t.Cleanup(func() { store.Close() })
	return NewServer(store)
}

func do(t *testing.T, h http.Handler, method, path, body string) *httptest.ResponseRecorder {
	t.Helper()
	var r *http.Request
	if body != "" {
		r = httptest.NewRequest(method, path, bytes.NewBufferString(body))
		r.Header.Set("Content-Type", "application/json")
	} else {
		r = httptest.NewRequest(method, path, nil)
	}
	w := httptest.NewRecorder()
	h.ServeHTTP(w, r)
	return w
}

func decodeBook(t *testing.T, w *httptest.ResponseRecorder) Book {
	t.Helper()
	var b Book
	if err := json.Unmarshal(w.Body.Bytes(), &b); err != nil {
		t.Fatalf("decode book: %v (body=%s)", err, w.Body.String())
	}
	return b
}

func expectStatus(t *testing.T, w *httptest.ResponseRecorder, want int) {
	t.Helper()
	if w.Code != want {
		t.Fatalf("status = %d, want %d (body=%s)", w.Code, want, w.Body.String())
	}
}

const dune = `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}`

func TestBookCRUD(t *testing.T) {
	srv := newTestServer(t)

	// Create
	w := do(t, srv, "POST", "/books", dune)
	expectStatus(t, w, http.StatusCreated)
	created := decodeBook(t, w)
	if created.ID == 0 || created.Title != "Dune" || created.Year != 1965 {
		t.Fatalf("unexpected created book: %+v", created)
	}
	if loc := w.Header().Get("Location"); loc != "/books/"+itoa(created.ID) {
		t.Errorf("Location = %q", loc)
	}

	// Get
	w = do(t, srv, "GET", "/books/"+itoa(created.ID), "")
	expectStatus(t, w, http.StatusOK)
	if got := decodeBook(t, w); got != created {
		t.Errorf("get = %+v, want %+v", got, created)
	}

	// Update
	w = do(t, srv, "PUT", "/books/"+itoa(created.ID),
		`{"title":"Dune Messiah","author":"Frank Herbert","year":1969,"isbn":""}`)
	expectStatus(t, w, http.StatusOK)
	updated := decodeBook(t, w)
	if updated.ID != created.ID || updated.Title != "Dune Messiah" || updated.Year != 1969 {
		t.Errorf("unexpected updated book: %+v", updated)
	}

	// Delete
	w = do(t, srv, "DELETE", "/books/"+itoa(created.ID), "")
	expectStatus(t, w, http.StatusNoContent)

	// Gone
	w = do(t, srv, "GET", "/books/"+itoa(created.ID), "")
	expectStatus(t, w, http.StatusNotFound)
}

func TestListWithAuthorFilter(t *testing.T) {
	srv := newTestServer(t)

	w := do(t, srv, "GET", "/books", "")
	expectStatus(t, w, http.StatusOK)
	if strings.TrimSpace(w.Body.String()) != "[]" {
		t.Errorf("empty list body = %s, want []", w.Body.String())
	}

	do(t, srv, "POST", "/books", dune)
	do(t, srv, "POST", "/books", `{"title":"Children of Dune","author":"Frank Herbert","year":1976}`)
	do(t, srv, "POST", "/books", `{"title":"Neuromancer","author":"William Gibson","year":1984}`)

	w = do(t, srv, "GET", "/books", "")
	expectStatus(t, w, http.StatusOK)
	var all []Book
	if err := json.Unmarshal(w.Body.Bytes(), &all); err != nil || len(all) != 3 {
		t.Fatalf("list all: len=%d err=%v", len(all), err)
	}

	w = do(t, srv, "GET", "/books?author=Frank+Herbert", "")
	expectStatus(t, w, http.StatusOK)
	var herbert []Book
	if err := json.Unmarshal(w.Body.Bytes(), &herbert); err != nil {
		t.Fatalf("decode filtered: %v", err)
	}
	if len(herbert) != 2 {
		t.Fatalf("filtered len = %d, want 2", len(herbert))
	}
	for _, b := range herbert {
		if b.Author != "Frank Herbert" {
			t.Errorf("unexpected author in filtered result: %q", b.Author)
		}
	}
}

func TestCreateValidation(t *testing.T) {
	srv := newTestServer(t)

	cases := []struct {
		name  string
		body  string
		field string
	}{
		{"missing title", `{"author":"A","year":2000}`, "title"},
		{"blank title", `{"title":"   ","author":"A","year":2000}`, "title"},
		{"missing author", `{"title":"T","year":2000}`, "author"},
		{"negative year", `{"title":"T","author":"A","year":-5}`, "year"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			w := do(t, srv, "POST", "/books", tc.body)
			expectStatus(t, w, http.StatusBadRequest)
			if !strings.Contains(w.Body.String(), `"field":"`+tc.field+`"`) {
				t.Errorf("body %s does not report field %q", w.Body.String(), tc.field)
			}
		})
	}

	w := do(t, srv, "POST", "/books", `{not json`)
	expectStatus(t, w, http.StatusBadRequest)

	w = do(t, srv, "POST", "/books", `{"title":"T","author":"A","year":1,"bogus":true}`)
	expectStatus(t, w, http.StatusBadRequest)
}

func TestNotFoundAndBadIDs(t *testing.T) {
	srv := newTestServer(t)

	expectStatus(t, do(t, srv, "GET", "/books/999", ""), http.StatusNotFound)
	expectStatus(t, do(t, srv, "PUT", "/books/999", dune), http.StatusNotFound)
	expectStatus(t, do(t, srv, "DELETE", "/books/999", ""), http.StatusNotFound)

	expectStatus(t, do(t, srv, "GET", "/books/abc", ""), http.StatusBadRequest)
	expectStatus(t, do(t, srv, "GET", "/books/0", ""), http.StatusBadRequest)
	expectStatus(t, do(t, srv, "DELETE", "/books/-1", ""), http.StatusBadRequest)
}

func TestUpdateValidation(t *testing.T) {
	srv := newTestServer(t)
	w := do(t, srv, "POST", "/books", dune)
	id := decodeBook(t, w).ID

	expectStatus(t, do(t, srv, "PUT", "/books/"+itoa(id), `{"title":"","author":"A","year":1}`), http.StatusBadRequest)
}

func TestHealth(t *testing.T) {
	srv := newTestServer(t)
	w := do(t, srv, "GET", "/health", "")
	expectStatus(t, w, http.StatusOK)
	if !strings.Contains(w.Body.String(), `"ok"`) {
		t.Errorf("health body = %s", w.Body.String())
	}
}

func itoa(n int64) string {
	return strconv.FormatInt(n, 10)
}
