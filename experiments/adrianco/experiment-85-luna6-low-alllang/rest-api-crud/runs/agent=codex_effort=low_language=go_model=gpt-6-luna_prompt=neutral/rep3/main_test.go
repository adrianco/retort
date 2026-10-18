package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"net/url"
	"testing"
)

func testAPI(t *testing.T) *API {
	t.Helper()
	db, err := OpenDB("file:" + t.Name() + "?mode=memory&cache=shared")
	if err != nil {
		t.Fatal(err)
	}
	api, err := NewAPI(db)
	if err != nil {
		db.Close()
		t.Fatal(err)
	}
	t.Cleanup(func() { db.Close() })
	return api
}

func request(t *testing.T, api *API, method, path, body string) *httptest.ResponseRecorder {
	t.Helper()
	var r *bytes.Reader
	if body != "" {
		r = bytes.NewReader([]byte(body))
	} else {
		r = bytes.NewReader(nil)
	}
	u, err := url.Parse(path)
	if err != nil {
		t.Fatal(err)
	}
	req := &http.Request{Method: method, URL: u, Header: make(http.Header), Body: http.NoBody}
	if body != "" {
		req.Body = http.NoBody
		req.Body = ioNopCloser{Reader: r}
	}
	w := httptest.NewRecorder()
	api.ServeHTTP(w, req)
	return w
}

type ioNopCloser struct{ *bytes.Reader }

func (r ioNopCloser) Close() error { return nil }

func TestCreateGetUpdateDeleteBook(t *testing.T) {
	api := testAPI(t)
	resp := request(t, api, http.MethodPost, "/books", `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}`)
	if resp.Code != http.StatusCreated {
		t.Fatalf("create status = %d", resp.Code)
	}
	var created Book
	if err := json.NewDecoder(resp.Body).Decode(&created); err != nil {
		t.Fatal(err)
	}
	if created.ID == 0 || created.Title != "Dune" {
		t.Fatalf("unexpected created book: %+v", created)
	}
	resp = request(t, api, http.MethodGet, "/books/1", "")
	if resp.Code != http.StatusOK {
		t.Fatalf("get status = %d", resp.Code)
	}
	resp = request(t, api, http.MethodPut, "/books/1", `{"title":"Dune Messiah","author":"Frank Herbert","year":1969,"isbn":"x"}`)
	if resp.Code != http.StatusOK {
		t.Fatalf("update status = %d", resp.Code)
	}
	resp = request(t, api, http.MethodDelete, "/books/1", "")
	if resp.Code != http.StatusNoContent {
		t.Fatalf("delete status = %d", resp.Code)
	}
	resp = request(t, api, http.MethodGet, "/books/1", "")
	if resp.Code != http.StatusNotFound {
		t.Fatalf("missing get status = %d", resp.Code)
	}
}

func TestListFilterAndRequiredFields(t *testing.T) {
	api := testAPI(t)
	for _, body := range []string{`{"title":"One","author":"Ada"}`, `{"title":"Two","author":"Grace"}`, `{"title":"Three","author":"Ada"}`} {
		resp := request(t, api, http.MethodPost, "/books", body)
		if resp.Code != http.StatusCreated {
			t.Fatalf("create status = %d", resp.Code)
		}
	}
	resp := request(t, api, http.MethodGet, "/books?author=Ada", "")
	if resp.Code != http.StatusOK {
		t.Fatalf("list status = %d", resp.Code)
	}
	var books []Book
	if err := json.NewDecoder(resp.Body).Decode(&books); err != nil {
		t.Fatal(err)
	}
	if len(books) != 2 {
		t.Fatalf("filtered count = %d", len(books))
	}
	resp = request(t, api, http.MethodPost, "/books", `{"title":"Missing author"}`)
	if resp.Code != http.StatusBadRequest {
		t.Fatalf("validation status = %d", resp.Code)
	}
}

func TestHealth(t *testing.T) {
	api := testAPI(t)
	resp := request(t, api, http.MethodGet, "/health", "")
	if resp.Code != http.StatusOK {
		t.Fatalf("health status = %d", resp.Code)
	}
}
