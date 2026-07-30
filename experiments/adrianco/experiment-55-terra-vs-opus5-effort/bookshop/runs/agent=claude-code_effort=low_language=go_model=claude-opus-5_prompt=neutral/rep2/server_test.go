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

func newTestServer(t *testing.T) http.Handler {
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
	if body == "" {
		r = httptest.NewRequest(method, path, nil)
	} else {
		r = httptest.NewRequest(method, path, bytes.NewBufferString(body))
		r.Header.Set("Content-Type", "application/json")
	}
	w := httptest.NewRecorder()
	h.ServeHTTP(w, r)
	return w
}

func decode[T any](t *testing.T, w *httptest.ResponseRecorder) T {
	t.Helper()
	var v T
	if err := json.Unmarshal(w.Body.Bytes(), &v); err != nil {
		t.Fatalf("decode %q: %v", w.Body.String(), err)
	}
	return v
}

func TestHealth(t *testing.T) {
	w := do(t, newTestServer(t), http.MethodGet, "/health", "")
	if w.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", w.Code)
	}
	if got := decode[map[string]string](t, w)["status"]; got != "ok" {
		t.Fatalf("status field = %q, want ok", got)
	}
}

func TestCreateAndGetBook(t *testing.T) {
	h := newTestServer(t)

	w := do(t, h, http.MethodPost, "/books",
		`{"title":"Dune","author":"Herbert","year":1965,"isbn":"9780441013593"}`)
	if w.Code != http.StatusCreated {
		t.Fatalf("create status = %d, want 201 (%s)", w.Code, w.Body)
	}
	created := decode[Book](t, w)
	if created.ID == 0 {
		t.Fatal("created book has no ID")
	}

	w = do(t, h, http.MethodGet, "/books/"+itoa(created.ID), "")
	if w.Code != http.StatusOK {
		t.Fatalf("get status = %d, want 200", w.Code)
	}
	if got := decode[Book](t, w); got != created {
		t.Fatalf("got %+v, want %+v", got, created)
	}
}

func TestCreateValidation(t *testing.T) {
	h := newTestServer(t)
	cases := map[string]string{
		"missing title":  `{"author":"Herbert"}`,
		"missing author": `{"title":"Dune"}`,
		"blank title":    `{"title":"   ","author":"Herbert"}`,
		"malformed json": `{"title":`,
	}
	for name, body := range cases {
		t.Run(name, func(t *testing.T) {
			w := do(t, h, http.MethodPost, "/books", body)
			if w.Code != http.StatusBadRequest {
				t.Fatalf("status = %d, want 400", w.Code)
			}
			if decode[map[string]string](t, w)["error"] == "" {
				t.Fatal("expected an error message")
			}
		})
	}
}

func TestListAndAuthorFilter(t *testing.T) {
	h := newTestServer(t)
	for _, body := range []string{
		`{"title":"Dune","author":"Herbert","year":1965,"isbn":"a"}`,
		`{"title":"Dune Messiah","author":"Herbert","year":1969,"isbn":"b"}`,
		`{"title":"Neuromancer","author":"Gibson","year":1984,"isbn":"c"}`,
	} {
		if w := do(t, h, http.MethodPost, "/books", body); w.Code != http.StatusCreated {
			t.Fatalf("seed failed: %s", w.Body)
		}
	}

	all := decode[[]Book](t, do(t, h, http.MethodGet, "/books", ""))
	if len(all) != 3 {
		t.Fatalf("len(all) = %d, want 3", len(all))
	}

	filtered := decode[[]Book](t, do(t, h, http.MethodGet, "/books?author=Herbert", ""))
	if len(filtered) != 2 {
		t.Fatalf("len(filtered) = %d, want 2", len(filtered))
	}
	for _, b := range filtered {
		if b.Author != "Herbert" {
			t.Fatalf("unexpected author %q in filtered results", b.Author)
		}
	}

	empty := decode[[]Book](t, do(t, h, http.MethodGet, "/books?author=Nobody", ""))
	if len(empty) != 0 {
		t.Fatalf("len(empty) = %d, want 0", len(empty))
	}
	if strings.TrimSpace(do(t, h, http.MethodGet, "/books?author=Nobody", "").Body.String()) != "[]" {
		t.Fatal("empty list should serialize as [], not null")
	}
}

func TestUpdateBook(t *testing.T) {
	h := newTestServer(t)
	created := decode[Book](t, do(t, h, http.MethodPost, "/books",
		`{"title":"Dune","author":"Herbert","year":1965,"isbn":"a"}`))

	w := do(t, h, http.MethodPut, "/books/"+itoa(created.ID),
		`{"title":"Dune (rev)","author":"Frank Herbert","year":1966,"isbn":"z"}`)
	if w.Code != http.StatusOK {
		t.Fatalf("update status = %d, want 200 (%s)", w.Code, w.Body)
	}
	updated := decode[Book](t, w)
	want := Book{ID: created.ID, Title: "Dune (rev)", Author: "Frank Herbert", Year: 1966, ISBN: "z"}
	if updated != want {
		t.Fatalf("got %+v, want %+v", updated, want)
	}

	// Persisted, not just echoed back.
	if got := decode[Book](t, do(t, h, http.MethodGet, "/books/"+itoa(created.ID), "")); got != want {
		t.Fatalf("after re-read got %+v, want %+v", got, want)
	}

	if w := do(t, h, http.MethodPut, "/books/9999", `{"title":"x","author":"y"}`); w.Code != http.StatusNotFound {
		t.Fatalf("update missing status = %d, want 404", w.Code)
	}
}

func TestDeleteBook(t *testing.T) {
	h := newTestServer(t)
	created := decode[Book](t, do(t, h, http.MethodPost, "/books", `{"title":"Dune","author":"Herbert"}`))

	if w := do(t, h, http.MethodDelete, "/books/"+itoa(created.ID), ""); w.Code != http.StatusNoContent {
		t.Fatalf("delete status = %d, want 204", w.Code)
	}
	if w := do(t, h, http.MethodGet, "/books/"+itoa(created.ID), ""); w.Code != http.StatusNotFound {
		t.Fatalf("get after delete status = %d, want 404", w.Code)
	}
	if w := do(t, h, http.MethodDelete, "/books/"+itoa(created.ID), ""); w.Code != http.StatusNotFound {
		t.Fatalf("second delete status = %d, want 404", w.Code)
	}
}

func TestInvalidAndMissingIDs(t *testing.T) {
	h := newTestServer(t)
	if w := do(t, h, http.MethodGet, "/books/abc", ""); w.Code != http.StatusBadRequest {
		t.Fatalf("status = %d, want 400", w.Code)
	}
	if w := do(t, h, http.MethodGet, "/books/42", ""); w.Code != http.StatusNotFound {
		t.Fatalf("status = %d, want 404", w.Code)
	}
}

func itoa(id int64) string { return strconv.FormatInt(id, 10) }
