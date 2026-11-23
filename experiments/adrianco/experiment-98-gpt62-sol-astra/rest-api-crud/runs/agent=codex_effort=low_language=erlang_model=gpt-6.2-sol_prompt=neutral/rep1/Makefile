ERLC ?= erlc
ERL ?= erl

.PHONY: all test test-http run clean
all: ebin/book_api.beam ebin/book_store.beam

ebin/%.beam: %.erl
	mkdir -p ebin
	$(ERLC) -Werror -o ebin $<

test: all ebin/book_api_tests.beam
	$(ERL) -noshell -pa ebin -eval 'case eunit:test(book_api_tests, [verbose]) of ok -> halt(0); _ -> halt(1) end.'

test-http:
	BOOK_API_HTTP_TEST=1 $(MAKE) test

run: all
	$(ERL) -noshell -pa ebin -s book_api run

clean:
	rm -rf ebin
