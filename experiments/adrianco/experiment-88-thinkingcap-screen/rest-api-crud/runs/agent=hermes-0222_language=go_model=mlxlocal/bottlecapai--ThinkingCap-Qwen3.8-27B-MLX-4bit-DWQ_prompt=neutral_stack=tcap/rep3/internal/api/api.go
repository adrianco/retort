// Package api wires the book store to HTTP handlers via Gin.
package api

import (
	"errors"
	"net/http"
	"strconv"
	"strings"

	"github.com/gin-gonic/gin"

	"bookapi/internal/store"
)

// New builds the HTTP handler for the book API backed by st.
func New(st *store.Store) http.Handler {
	gin.SetMode(gin.ReleaseMode)
	r := gin.New()
	r.Use(gin.Recovery())

	s := &server{store: st}
	r.GET("/", s.handleRoot)
	r.GET("/health", s.handleHealth)
	r.POST("/books", s.handleCreate)
	r.GET("/books", s.handleList)
	r.GET("/books/:id", s.handleGet)
	r.PUT("/books/:id", s.handleUpdate)
	r.DELETE("/books/:id", s.handleDelete)
	return r
}

type server struct {
	store *store.Store
}

// bookResponse is the JSON representation of a book.
type bookResponse struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

func toResponse(b store.Book) bookResponse {
	return bookResponse{ID: b.ID, Title: b.Title, Author: b.Author, Year: b.Year, ISBN: b.ISBN}
}

func writeError(c *gin.Context, status int, msg string) {
	c.JSON(status, gin.H{"error": msg})
}

// createRequest is the POST /books body. Title and author are required;
// year and isbn are optional (zero/empty when omitted).
type createRequest struct {
	Title  string  `json:"title"`
	Author string  `json:"author"`
	Year   *int    `json:"year"`
	ISBN   *string `json:"isbn"`
}

// updateRequest is the PUT /books/{id} body. Title and author are
// required; year and isbn, when omitted, keep their stored values.
type updateRequest struct {
	Title  string  `json:"title"`
	Author string  `json:"author"`
	Year   *int    `json:"year"`
	ISBN   *string `json:"isbn"`
}

const maxYear = 9999

func (s *server) handleRoot(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"service": "book-api",
		"endpoints": []string{"/health", "/books", "/books/{id}"},
	})
}

func (s *server) handleHealth(c *gin.Context) {
	if err := s.store.Ping(c.Request.Context()); err != nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{"status": "error", "error": "database unreachable"})
		return
	}
	c.JSON(http.StatusOK, gin.H{"status": "ok"})
}

func (s *server) handleCreate(c *gin.Context) {
	var req createRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		writeError(c, http.StatusBadRequest, "invalid JSON body: "+err.Error())
		return
	}
	title := strings.TrimSpace(req.Title)
	author := strings.TrimSpace(req.Author)
	if title == "" {
		writeError(c, http.StatusBadRequest, "title is required")
		return
	}
	if author == "" {
		writeError(c, http.StatusBadRequest, "author is required")
		return
	}
	year := 0
	if req.Year != nil {
		year = *req.Year
		if year < 0 || year > maxYear {
			writeError(c, http.StatusBadRequest, "year must be between 0 and 9999")
			return
		}
	}
	isbn := ""
	if req.ISBN != nil {
		isbn = *req.ISBN
	}

	book, err := s.store.Create(c.Request.Context(), store.Book{
		Title: title, Author: author, Year: year, ISBN: isbn,
	})
	if err != nil {
		writeError(c, http.StatusInternalServerError, "failed to create book")
		return
	}
	c.JSON(http.StatusCreated, toResponse(book))
}

func (s *server) handleList(c *gin.Context) {
	author := strings.TrimSpace(c.Query("author"))
	books, err := s.store.List(c.Request.Context(), author)
	if err != nil {
		writeError(c, http.StatusInternalServerError, "failed to list books")
		return
	}
	out := make([]bookResponse, 0, len(books))
	for _, b := range books {
		out = append(out, toResponse(b))
	}
	c.JSON(http.StatusOK, out)
}

func (s *server) handleGet(c *gin.Context) {
	id, err := parseID(c.Param("id"))
	if err != nil {
		writeError(c, http.StatusBadRequest, "id must be an integer")
		return
	}
	book, err := s.store.Get(c.Request.Context(), id)
	if err != nil {
		if errors.Is(err, store.ErrNotFound) {
			writeError(c, http.StatusNotFound, "book not found")
			return
		}
		writeError(c, http.StatusInternalServerError, "failed to get book")
		return
	}
	c.JSON(http.StatusOK, toResponse(book))
}

func (s *server) handleUpdate(c *gin.Context) {
	id, err := parseID(c.Param("id"))
	if err != nil {
		writeError(c, http.StatusBadRequest, "id must be an integer")
		return
	}
	var req updateRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		writeError(c, http.StatusBadRequest, "invalid JSON body: "+err.Error())
		return
	}
	title := strings.TrimSpace(req.Title)
	author := strings.TrimSpace(req.Author)
	if title == "" {
		writeError(c, http.StatusBadRequest, "title is required")
		return
	}
	if author == "" {
		writeError(c, http.StatusBadRequest, "author is required")
		return
	}

	existing, err := s.store.Get(c.Request.Context(), id)
	if err != nil {
		if errors.Is(err, store.ErrNotFound) {
			writeError(c, http.StatusNotFound, "book not found")
			return
		}
		writeError(c, http.StatusInternalServerError, "failed to get book")
		return
	}

	year := existing.Year
	if req.Year != nil {
		if *req.Year < 0 || *req.Year > maxYear {
			writeError(c, http.StatusBadRequest, "year must be between 0 and 9999")
			return
		}
		year = *req.Year
	}
	isbn := existing.ISBN
	if req.ISBN != nil {
		isbn = *req.ISBN
	}

	updated, err := s.store.Update(c.Request.Context(), store.Book{
		ID: id, Title: title, Author: author, Year: year, ISBN: isbn,
	})
	if err != nil {
		writeError(c, http.StatusInternalServerError, "failed to update book")
		return
	}
	c.JSON(http.StatusOK, toResponse(updated))
}

func (s *server) handleDelete(c *gin.Context) {
	id, err := parseID(c.Param("id"))
	if err != nil {
		writeError(c, http.StatusBadRequest, "id must be an integer")
		return
	}
	if err := s.store.Delete(c.Request.Context(), id); err != nil {
		if errors.Is(err, store.ErrNotFound) {
			writeError(c, http.StatusNotFound, "book not found")
			return
		}
		writeError(c, http.StatusInternalServerError, "failed to delete book")
		return
	}
	c.Status(http.StatusNoContent)
}

func parseID(raw string) (int64, error) {
	id, err := strconv.ParseInt(raw, 10, 64)
	if err != nil || id <= 0 {
		return 0, errors.New("invalid id")
	}
	return id, nil
}
