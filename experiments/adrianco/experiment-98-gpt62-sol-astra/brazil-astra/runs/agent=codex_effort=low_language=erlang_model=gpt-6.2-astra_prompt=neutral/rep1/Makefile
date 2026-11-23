.PHONY: build test run clean
build:
	@erlc -Werror soccer_data.erl soccer_query.erl soccer_mcp.erl
test: build
	@erlc -Werror soccer_tests.erl
	erl -noshell -eval 'case eunit:test(soccer_tests,[verbose]) of ok -> halt(0); _ -> halt(1) end.'
run: build
	@erl -noshell -s soccer_mcp main -s init stop
clean:
	rm -f soccer_data.beam soccer_query.beam soccer_mcp.beam soccer_tests.beam
