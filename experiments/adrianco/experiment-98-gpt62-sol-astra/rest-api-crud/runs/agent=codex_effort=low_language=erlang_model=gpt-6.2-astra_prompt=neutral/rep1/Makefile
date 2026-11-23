.PHONY: build test run
build:
	erlc -Werror books.erl
test: build
	erlc -Werror books_tests.erl
	erl -noshell -eval 'case eunit:test(books_tests, [verbose]) of ok -> halt(0); _ -> halt(1) end.'
run: build
	erl -noshell -s books run
