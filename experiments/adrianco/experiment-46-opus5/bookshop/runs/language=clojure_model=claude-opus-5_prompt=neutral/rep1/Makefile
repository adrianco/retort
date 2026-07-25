.PHONY: test run repl clean

test:
	./test.sh

run:
	./run.sh

repl:
	sh -c '. ./bin/java-env.sh && clojure -A:test'

clean:
	rm -rf .cpcache books.db
