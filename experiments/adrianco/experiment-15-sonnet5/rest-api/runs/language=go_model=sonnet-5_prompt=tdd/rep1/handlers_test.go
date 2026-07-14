package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strconv"
	"testing"
)

func newTestServer(t *testing.T) http.Handler {
	t.Helper()
	s := newTestStore(t)
	return NewRouter(s)
}

func doRequest(t *testing.T, h http.Handler, method, path string, body any) *httptest.ResponseRecorder {
	t.Helper()
	var reader *bytes.Reader
	if body != nil {
		b, err := json.Marshal(body)
		if err != nil {
			t.Fatalf("marshal body: %v", err)
		}
		reader = bytes.NewReader(b)
	} else {
		reader = bytes.NewReader(nil)
	}
	req := httptest.NewRequest(method, path, reader)
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

func TestHealthCheck(t *testing.T) {
	h := newTestServer(t)
	rec := doRequest(t, h, http.MethodGet, "/health", nil)

	if rec.Code != http.StatusOK {
		t.Fatalf("GET /health status = %d, want %d", rec.Code, http.StatusOK)
	}
	var resp map[string]string
	if err := json.Unmarshal(rec.Body.Bytes(), &resp); err != nil {
		t.Fatalf("unmarshal response: %v", err)
	}
	if resp["status"] != "ok" {
		t.Fatalf("health response = %v, want status ok", resp)
	}
}

func TestCreateBook(t *testing.T) {
	h := newTestServer(t)
	rec := doRequest(t, h, http.MethodPost, "/books", Book{
		Title: "The Hobbit", Author: "J.R.R. Tolkien", Year: 1937, ISBN: "978-0345339683",
	})

	if rec.Code != http.StatusCreated {
		t.Fatalf("POST /books status = %d, want %d, body=%s", rec.Code, http.StatusCreated, rec.Body.String())
	}
	var created Book
	if err := json.Unmarshal(rec.Body.Bytes(), &created); err != nil {
		t.Fatalf("unmarshal response: %v", err)
	}
	if created.ID == 0 {
		t.Fatalf("created book has no ID: %+v", created)
	}
	if created.Title != "The Hobbit" {
		t.Fatalf("created book title = %q, want %q", created.Title, "The Hobbit")
	}
}

func TestCreateBookValidation(t *testing.T) {
	h := newTestServer(t)

	tests := []struct {
		name string
		book Book
	}{
		{"missing title", Book{Author: "Someone"}},
		{"missing author", Book{Title: "Something"}},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			rec := doRequest(t, h, http.MethodPost, "/books", tt.book)
			if rec.Code != http.StatusBadRequest {
				t.Fatalf("POST /books status = %d, want %d, body=%s", rec.Code, http.StatusBadRequest, rec.Body.String())
			}
		})
	}
}

func TestListBooksAndFilterByAuthor(t *testing.T) {
	h := newTestServer(t)
	doRequest(t, h, http.MethodPost, "/books", Book{Title: "The Hobbit", Author: "J.R.R. Tolkien", Year: 1937})
	doRequest(t, h, http.MethodPost, "/books", Book{Title: "Dune", Author: "Frank Herbert", Year: 1965})

	rec := doRequest(t, h, http.MethodGet, "/books", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("GET /books status = %d, want %d", rec.Code, http.StatusOK)
	}
	var books []Book
	if err := json.Unmarshal(rec.Body.Bytes(), &books); err != nil {
		t.Fatalf("unmarshal response: %v", err)
	}
	if len(books) != 2 {
		t.Fatalf("GET /books returned %d books, want 2", len(books))
	}

	rec = doRequest(t, h, http.MethodGet, "/books?author=Frank+Herbert", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("GET /books?author= status = %d, want %d", rec.Code, http.StatusOK)
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &books); err != nil {
		t.Fatalf("unmarshal response: %v", err)
	}
	if len(books) != 1 || books[0].Author != "Frank Herbert" {
		t.Fatalf("GET /books?author=Frank+Herbert = %+v, want single book by Frank Herbert", books)
	}
}

func TestGetBookByID(t *testing.T) {
	h := newTestServer(t)
	createRec := doRequest(t, h, http.MethodPost, "/books", Book{Title: "Dune", Author: "Frank Herbert", Year: 1965})
	var created Book
	json.Unmarshal(createRec.Body.Bytes(), &created)

	rec := doRequest(t, h, http.MethodGet, "/books/"+strconv.FormatInt(created.ID, 10), nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("GET /books/{id} status = %d, want %d", rec.Code, http.StatusOK)
	}
	var got Book
	json.Unmarshal(rec.Body.Bytes(), &got)
	if got.ID != created.ID {
		t.Fatalf("GET /books/{id} = %+v, want ID %d", got, created.ID)
	}
}

func TestGetBookNotFound(t *testing.T) {
	h := newTestServer(t)
	rec := doRequest(t, h, http.MethodGet, "/books/999", nil)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("GET /books/999 status = %d, want %d", rec.Code, http.StatusNotFound)
	}
}

func TestUpdateBook(t *testing.T) {
	h := newTestServer(t)
	createRec := doRequest(t, h, http.MethodPost, "/books", Book{Title: "Dune", Author: "Frank Herbert", Year: 1965})
	var created Book
	json.Unmarshal(createRec.Body.Bytes(), &created)

	rec := doRequest(t, h, http.MethodPut, "/books/"+strconv.FormatInt(created.ID, 10), Book{
		Title: "Dune Messiah", Author: "Frank Herbert", Year: 1969,
	})
	if rec.Code != http.StatusOK {
		t.Fatalf("PUT /books/{id} status = %d, want %d, body=%s", rec.Code, http.StatusOK, rec.Body.String())
	}
	var updated Book
	json.Unmarshal(rec.Body.Bytes(), &updated)
	if updated.Title != "Dune Messiah" {
		t.Fatalf("updated book = %+v, want title Dune Messiah", updated)
	}
}

func TestUpdateBookNotFound(t *testing.T) {
	h := newTestServer(t)
	rec := doRequest(t, h, http.MethodPut, "/books/999", Book{Title: "X", Author: "Y"})
	if rec.Code != http.StatusNotFound {
		t.Fatalf("PUT /books/999 status = %d, want %d", rec.Code, http.StatusNotFound)
	}
}

func TestUpdateBookValidation(t *testing.T) {
	h := newTestServer(t)
	createRec := doRequest(t, h, http.MethodPost, "/books", Book{Title: "Dune", Author: "Frank Herbert", Year: 1965})
	var created Book
	json.Unmarshal(createRec.Body.Bytes(), &created)

	rec := doRequest(t, h, http.MethodPut, "/books/"+strconv.FormatInt(created.ID, 10), Book{Title: "", Author: "Frank Herbert"})
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("PUT /books/{id} status = %d, want %d", rec.Code, http.StatusBadRequest)
	}
}

func TestDeleteBook(t *testing.T) {
	h := newTestServer(t)
	createRec := doRequest(t, h, http.MethodPost, "/books", Book{Title: "Dune", Author: "Frank Herbert", Year: 1965})
	var created Book
	json.Unmarshal(createRec.Body.Bytes(), &created)

	rec := doRequest(t, h, http.MethodDelete, "/books/"+strconv.FormatInt(created.ID, 10), nil)
	if rec.Code != http.StatusNoContent {
		t.Fatalf("DELETE /books/{id} status = %d, want %d", rec.Code, http.StatusNoContent)
	}

	rec = doRequest(t, h, http.MethodGet, "/books/"+strconv.FormatInt(created.ID, 10), nil)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("GET after delete status = %d, want %d", rec.Code, http.StatusNotFound)
	}
}

func TestDeleteBookNotFound(t *testing.T) {
	h := newTestServer(t)
	rec := doRequest(t, h, http.MethodDelete, "/books/999", nil)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("DELETE /books/999 status = %d, want %d", rec.Code, http.StatusNotFound)
	}
}
