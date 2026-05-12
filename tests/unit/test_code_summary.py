"""Tests for the deterministic code summary used by the web report."""

from __future__ import annotations

from pathlib import Path

from retort.reporting.code_summary import summarize_archive


def test_returns_none_for_missing_archive(tmp_path):
    assert summarize_archive(tmp_path / "nope", "python") is None


def test_returns_none_for_unknown_language(tmp_path):
    (tmp_path / "main.py").write_text("def x(): pass\n")
    assert summarize_archive(tmp_path, "brainfuck") is None


def test_returns_none_for_no_source_files(tmp_path):
    (tmp_path / "README.md").write_text("# README\n")
    assert summarize_archive(tmp_path, "python") is None


def test_python_summary(tmp_path):
    (tmp_path / "app.py").write_text(
        "class Book:\n    pass\n\n"
        "def list_books():\n    return []\n\n"
        "def create_book(title):\n    return None\n"
    )
    (tmp_path / "test_app.py").write_text(
        "def test_list():\n    assert list_books() == []\n"
    )
    summary = summarize_archive(tmp_path, "python")
    assert summary is not None
    assert summary.n_files == 2
    assert summary.n_test_files == 1
    assert summary.total_loc > 0
    assert summary.test_loc > 0

    # Symbols extracted from app.py
    app = next(f for f in summary.files if f.relpath == "app.py")
    assert "class Book" in app.symbols
    assert "def list_books" in app.symbols
    assert "def create_book" in app.symbols
    assert app.is_test is False

    # Test file flagged
    test_file = next(f for f in summary.files if f.relpath == "test_app.py")
    assert test_file.is_test is True


def test_go_summary(tmp_path):
    (tmp_path / "main.go").write_text(
        "package main\n\n"
        "type Book struct { ID int }\n\n"
        "func ListBooks() []Book { return nil }\n\n"
        "func (s *Server) CreateBook() error { return nil }\n"
    )
    (tmp_path / "main_test.go").write_text(
        "package main\n\nfunc TestList(t *testing.T) {}\n"
    )
    summary = summarize_archive(tmp_path, "go")
    assert summary is not None
    assert summary.n_files == 2
    assert summary.n_test_files == 1

    main = next(f for f in summary.files if f.relpath == "main.go")
    assert "type Book" in main.symbols
    assert "func ListBooks" in main.symbols
    assert "func CreateBook" in main.symbols  # method receiver stripped


def test_rust_summary(tmp_path):
    (tmp_path / "lib.rs").write_text(
        "pub struct Book { pub id: u32 }\n"
        "pub enum Status { Active, Closed }\n"
        "pub async fn list_books() -> Vec<Book> { vec![] }\n"
    )
    summary = summarize_archive(tmp_path, "rust")
    assert summary is not None
    syms = summary.files[0].symbols
    assert "struct Book" in syms
    assert "enum Status" in syms
    assert "fn list_books" in syms


def test_skips_build_artifacts(tmp_path):
    (tmp_path / "main.py").write_text("def real(): pass\n")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "leaked.py").write_text("def fake(): pass\n")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "x.py").write_text("def cached(): pass\n")

    summary = summarize_archive(tmp_path, "python")
    assert summary is not None
    assert summary.n_files == 1
    assert summary.files[0].relpath == "main.py"


def test_typescript_summary(tmp_path):
    (tmp_path / "app.ts").write_text(
        "export const main = () => 1;\n"
        "export class Server { run() {} }\n"
        "export async function listBooks() { return []; }\n"
    )
    summary = summarize_archive(tmp_path, "typescript")
    assert summary is not None
    syms = summary.files[0].symbols
    assert "const main" in syms
    assert "class Server" in syms
    assert "function listBooks" in syms


def test_elixir_summary(tmp_path):
    (tmp_path / "books.ex").write_text(
        "defmodule Books do\n"
        "  def list_books, do: []\n"
        "  def create_book(title), do: {:ok, title}\n"
        "  defp validate(book), do: book\n"
        "end\n"
    )
    (tmp_path / "books_test.exs").write_text(
        "defmodule BooksTest do\n"
        "  use ExUnit.Case\n"
        "  test 'list_books returns empty list' do\n"
        "    assert Books.list_books() == []\n"
        "  end\n"
        "end\n"
    )
    summary = summarize_archive(tmp_path, "elixir")
    assert summary is not None
    assert summary.n_files == 2
    assert summary.n_test_files == 1

    src = next(f for f in summary.files if f.relpath == "books.ex")
    assert "defmodule Books" in src.symbols
    assert "def list_books" in src.symbols
    assert "def create_book" in src.symbols
    assert "defp validate" in src.symbols
    assert src.is_test is False

    test_file = next(f for f in summary.files if f.relpath == "books_test.exs")
    assert test_file.is_test is True


def test_erlang_summary(tmp_path):
    (tmp_path / "books.erl").write_text(
        "-module(books).\n"
        "-export([list_books/0, create_book/1]).\n"
        "list_books() -> [].\n"
        "create_book(Title) -> {ok, Title}.\n"
    )
    (tmp_path / "books_tests.erl").write_text(
        "-module(books_tests).\n"
        "list_books_test() -> [] = books:list_books().\n"
    )
    summary = summarize_archive(tmp_path, "erlang")
    assert summary is not None
    assert summary.n_files == 2
    assert summary.n_test_files == 1

    src = next(f for f in summary.files if f.relpath == "books.erl")
    assert "module books" in src.symbols
    assert src.is_test is False

    test_file = next(f for f in summary.files if f.relpath == "books_tests.erl")
    assert test_file.is_test is True
