package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strconv"
	"strings"
	"testing"
)

func newTestServer(t *testing.T) *Server {
	t.Helper()
	store, err := NewStore(":memory:")
	if err != nil {
		t.Fatalf("NewStore: %v", err)
	}
	t.Cleanup(func() { store.Close() })
	return NewServer(store)
}

func do(t *testing.T, srv *Server, method, path, body string) *httptest.ResponseRecorder {
	t.Helper()
	var r *http.Request
	if body != "" {
		r = httptest.NewRequest(method, path, strings.NewReader(body))
	} else {
		r = httptest.NewRequest(method, path, nil)
	}
	w := httptest.NewRecorder()
	srv.ServeHTTP(w, r)
	return w
}

func TestHealth(t *testing.T) {
	srv := newTestServer(t)
	w := do(t, srv, http.MethodGet, "/health", "")
	if w.Code != http.StatusOK {
		t.Fatalf("status = %d, want %d", w.Code, http.StatusOK)
	}
	var got map[string]string
	if err := json.Unmarshal(w.Body.Bytes(), &got); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if got["status"] != "ok" {
		t.Fatalf("status field = %q, want ok", got["status"])
	}
}

func TestCreateAndGetBook(t *testing.T) {
	srv := newTestServer(t)
	body := `{"title":"Go in Action","author":"Kennedy","year":2015,"isbn":"123"}`
	w := do(t, srv, http.MethodPost, "/books", body)
	if w.Code != http.StatusCreated {
		t.Fatalf("create status = %d, want %d (%s)", w.Code, http.StatusCreated, w.Body)
	}
	var created Book
	if err := json.Unmarshal(w.Body.Bytes(), &created); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if created.ID == 0 {
		t.Fatal("expected non-zero ID")
	}
	if created.Title != "Go in Action" || created.Author != "Kennedy" {
		t.Fatalf("unexpected book: %+v", created)
	}

	// Fetch it back.
	w = do(t, srv, http.MethodGet, "/books/"+itoa(created.ID), "")
	if w.Code != http.StatusOK {
		t.Fatalf("get status = %d, want %d", w.Code, http.StatusOK)
	}
	var fetched Book
	if err := json.Unmarshal(w.Body.Bytes(), &fetched); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if fetched != created {
		t.Fatalf("fetched %+v, want %+v", fetched, created)
	}
}

func TestCreateValidation(t *testing.T) {
	srv := newTestServer(t)
	cases := map[string]string{
		"missing title":  `{"author":"X"}`,
		"missing author": `{"title":"X"}`,
	}
	for name, body := range cases {
		t.Run(name, func(t *testing.T) {
			w := do(t, srv, http.MethodPost, "/books", body)
			if w.Code != http.StatusBadRequest {
				t.Fatalf("status = %d, want %d", w.Code, http.StatusBadRequest)
			}
		})
	}
}

func TestListWithAuthorFilter(t *testing.T) {
	srv := newTestServer(t)
	do(t, srv, http.MethodPost, "/books", `{"title":"A","author":"Alice"}`)
	do(t, srv, http.MethodPost, "/books", `{"title":"B","author":"Bob"}`)
	do(t, srv, http.MethodPost, "/books", `{"title":"C","author":"Alice"}`)

	w := do(t, srv, http.MethodGet, "/books", "")
	var all []Book
	mustJSON(t, w, http.StatusOK, &all)
	if len(all) != 3 {
		t.Fatalf("len(all) = %d, want 3", len(all))
	}

	w = do(t, srv, http.MethodGet, "/books?author=Alice", "")
	var alice []Book
	mustJSON(t, w, http.StatusOK, &alice)
	if len(alice) != 2 {
		t.Fatalf("len(alice) = %d, want 2", len(alice))
	}
	for _, b := range alice {
		if b.Author != "Alice" {
			t.Fatalf("got author %q in Alice filter", b.Author)
		}
	}
}

func TestUpdateBook(t *testing.T) {
	srv := newTestServer(t)
	w := do(t, srv, http.MethodPost, "/books", `{"title":"Old","author":"Auth","year":2000,"isbn":"1"}`)
	var created Book
	mustJSON(t, w, http.StatusCreated, &created)

	w = do(t, srv, http.MethodPut, "/books/"+itoa(created.ID),
		`{"title":"New","author":"Auth","year":2020,"isbn":"2"}`)
	var updated Book
	mustJSON(t, w, http.StatusOK, &updated)
	if updated.Title != "New" || updated.Year != 2020 || updated.ID != created.ID {
		t.Fatalf("unexpected update: %+v", updated)
	}

	// Updating a non-existent book yields 404.
	w = do(t, srv, http.MethodPut, "/books/99999", `{"title":"X","author":"Y"}`)
	if w.Code != http.StatusNotFound {
		t.Fatalf("status = %d, want %d", w.Code, http.StatusNotFound)
	}
}

func TestDeleteBook(t *testing.T) {
	srv := newTestServer(t)
	w := do(t, srv, http.MethodPost, "/books", `{"title":"Doomed","author":"Auth"}`)
	var created Book
	mustJSON(t, w, http.StatusCreated, &created)

	w = do(t, srv, http.MethodDelete, "/books/"+itoa(created.ID), "")
	if w.Code != http.StatusNoContent {
		t.Fatalf("delete status = %d, want %d", w.Code, http.StatusNoContent)
	}

	w = do(t, srv, http.MethodGet, "/books/"+itoa(created.ID), "")
	if w.Code != http.StatusNotFound {
		t.Fatalf("get-after-delete status = %d, want %d", w.Code, http.StatusNotFound)
	}

	// Deleting again is also a 404.
	w = do(t, srv, http.MethodDelete, "/books/"+itoa(created.ID), "")
	if w.Code != http.StatusNotFound {
		t.Fatalf("second delete status = %d, want %d", w.Code, http.StatusNotFound)
	}
}

func TestGetInvalidID(t *testing.T) {
	srv := newTestServer(t)
	w := do(t, srv, http.MethodGet, "/books/abc", "")
	if w.Code != http.StatusBadRequest {
		t.Fatalf("status = %d, want %d", w.Code, http.StatusBadRequest)
	}
}

// --- small helpers ---

func itoa(n int64) string {
	return strconv.FormatInt(n, 10)
}

func mustJSON(t *testing.T, w *httptest.ResponseRecorder, wantStatus int, v any) {
	t.Helper()
	if w.Code != wantStatus {
		t.Fatalf("status = %d, want %d (body: %s)", w.Code, wantStatus, w.Body)
	}
	if err := json.Unmarshal(w.Body.Bytes(), v); err != nil {
		t.Fatalf("decode: %v (body: %s)", err, w.Body)
	}
}
