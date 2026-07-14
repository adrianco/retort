package main

import (
	"bytes"
	"database/sql"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"strconv"
	"testing"

	_ "modernc.org/sqlite"
)

func newTestServer(t *testing.T) *Server {
	t.Helper()
	db, err := sql.Open("sqlite", ":memory:")
	if err != nil {
		t.Fatalf("open db: %v", err)
	}
	t.Cleanup(func() { db.Close() })
	store, err := NewStore(db)
	if err != nil {
		t.Fatalf("new store: %v", err)
	}
	return NewServer(store)
}

func doRequest(t *testing.T, h http.Handler, method, path string, body any) *httptest.ResponseRecorder {
	t.Helper()
	var rdr io.Reader
	if body != nil {
		buf, err := json.Marshal(body)
		if err != nil {
			t.Fatalf("marshal: %v", err)
		}
		rdr = bytes.NewReader(buf)
	}
	req := httptest.NewRequest(method, path, rdr)
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

func decode[T any](t *testing.T, rec *httptest.ResponseRecorder) T {
	t.Helper()
	var v T
	if err := json.Unmarshal(rec.Body.Bytes(), &v); err != nil {
		t.Fatalf("decode: %v body=%s", err, rec.Body.String())
	}
	return v
}

func TestHealth(t *testing.T) {
	srv := newTestServer(t)
	rec := doRequest(t, srv.Routes(), http.MethodGet, "/health", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", rec.Code)
	}
	got := decode[map[string]string](t, rec)
	if got["status"] != "ok" {
		t.Errorf("status = %q, want ok", got["status"])
	}
}

func TestCreateAndGetBook(t *testing.T) {
	srv := newTestServer(t)
	h := srv.Routes()

	in := Book{Title: "The Go Programming Language", Author: "Donovan & Kernighan", Year: 2015, ISBN: "978-0134190440"}
	rec := doRequest(t, h, http.MethodPost, "/books", in)
	if rec.Code != http.StatusCreated {
		t.Fatalf("POST status = %d, want 201: %s", rec.Code, rec.Body.String())
	}
	created := decode[Book](t, rec)
	if created.ID == 0 {
		t.Fatalf("created.ID = 0, want non-zero")
	}
	if created.Title != in.Title || created.Author != in.Author {
		t.Errorf("created = %+v, want title/author from input", created)
	}

	rec = doRequest(t, h, http.MethodGet, "/books/"+strconv.FormatInt(created.ID, 10), nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("GET status = %d, want 200", rec.Code)
	}
	got := decode[Book](t, rec)
	if got != created {
		t.Errorf("got = %+v, want %+v", got, created)
	}
}

func TestCreateBookValidation(t *testing.T) {
	srv := newTestServer(t)
	h := srv.Routes()

	cases := []struct {
		name string
		body Book
	}{
		{"missing title", Book{Author: "X"}},
		{"missing author", Book{Title: "X"}},
		{"both empty", Book{}},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			rec := doRequest(t, h, http.MethodPost, "/books", c.body)
			if rec.Code != http.StatusBadRequest {
				t.Errorf("status = %d, want 400, body=%s", rec.Code, rec.Body.String())
			}
		})
	}
}

func TestListBooksWithAuthorFilter(t *testing.T) {
	srv := newTestServer(t)
	h := srv.Routes()

	for _, b := range []Book{
		{Title: "A", Author: "Alice"},
		{Title: "B", Author: "Alice"},
		{Title: "C", Author: "Bob"},
	} {
		rec := doRequest(t, h, http.MethodPost, "/books", b)
		if rec.Code != http.StatusCreated {
			t.Fatalf("seed POST %s status = %d", b.Title, rec.Code)
		}
	}

	rec := doRequest(t, h, http.MethodGet, "/books", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("list all status = %d", rec.Code)
	}
	all := decode[[]Book](t, rec)
	if len(all) != 3 {
		t.Errorf("len(all) = %d, want 3", len(all))
	}

	rec = doRequest(t, h, http.MethodGet, "/books?author=Alice", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("list filtered status = %d", rec.Code)
	}
	filtered := decode[[]Book](t, rec)
	if len(filtered) != 2 {
		t.Fatalf("filtered len = %d, want 2", len(filtered))
	}
	for _, b := range filtered {
		if b.Author != "Alice" {
			t.Errorf("got author %q, want Alice", b.Author)
		}
	}
}

func TestUpdateBook(t *testing.T) {
	srv := newTestServer(t)
	h := srv.Routes()

	rec := doRequest(t, h, http.MethodPost, "/books", Book{Title: "Old", Author: "A"})
	if rec.Code != http.StatusCreated {
		t.Fatalf("create status = %d", rec.Code)
	}
	created := decode[Book](t, rec)

	updated := Book{Title: "New", Author: "B", Year: 2020, ISBN: "111"}
	rec = doRequest(t, h, http.MethodPut, "/books/"+strconv.FormatInt(created.ID, 10), updated)
	if rec.Code != http.StatusOK {
		t.Fatalf("PUT status = %d: %s", rec.Code, rec.Body.String())
	}
	got := decode[Book](t, rec)
	if got.Title != "New" || got.Author != "B" || got.Year != 2020 || got.ISBN != "111" {
		t.Errorf("got = %+v, want updated values", got)
	}
	if got.ID != created.ID {
		t.Errorf("ID changed: %d -> %d", created.ID, got.ID)
	}

	rec = doRequest(t, h, http.MethodPut, "/books/999999", updated)
	if rec.Code != http.StatusNotFound {
		t.Errorf("PUT missing status = %d, want 404", rec.Code)
	}
}

func TestDeleteBook(t *testing.T) {
	srv := newTestServer(t)
	h := srv.Routes()

	rec := doRequest(t, h, http.MethodPost, "/books", Book{Title: "T", Author: "A"})
	created := decode[Book](t, rec)

	rec = doRequest(t, h, http.MethodDelete, "/books/"+strconv.FormatInt(created.ID, 10), nil)
	if rec.Code != http.StatusNoContent {
		t.Fatalf("DELETE status = %d", rec.Code)
	}

	rec = doRequest(t, h, http.MethodGet, "/books/"+strconv.FormatInt(created.ID, 10), nil)
	if rec.Code != http.StatusNotFound {
		t.Errorf("GET after delete status = %d, want 404", rec.Code)
	}

	rec = doRequest(t, h, http.MethodDelete, "/books/999999", nil)
	if rec.Code != http.StatusNotFound {
		t.Errorf("DELETE missing status = %d, want 404", rec.Code)
	}
}

func TestGetBookNotFound(t *testing.T) {
	srv := newTestServer(t)
	rec := doRequest(t, srv.Routes(), http.MethodGet, "/books/42", nil)
	if rec.Code != http.StatusNotFound {
		t.Errorf("status = %d, want 404", rec.Code)
	}
}

func TestInvalidIDReturns400(t *testing.T) {
	srv := newTestServer(t)
	rec := doRequest(t, srv.Routes(), http.MethodGet, "/books/abc", nil)
	if rec.Code != http.StatusBadRequest {
		t.Errorf("status = %d, want 400", rec.Code)
	}
}

func TestMethodNotAllowed(t *testing.T) {
	srv := newTestServer(t)
	rec := doRequest(t, srv.Routes(), http.MethodPatch, "/books", nil)
	if rec.Code != http.StatusMethodNotAllowed {
		t.Errorf("status = %d, want 405", rec.Code)
	}
}

func TestMalformedJSON(t *testing.T) {
	srv := newTestServer(t)
	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBufferString("{not-json"))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	srv.Routes().ServeHTTP(rec, req)
	if rec.Code != http.StatusBadRequest {
		t.Errorf("status = %d, want 400", rec.Code)
	}
}
