# Convenience wrapper around the Clojure CLI.
#
# On macOS `/usr/bin/java` is a stub that only finds JDKs registered under
# /Library/Java/JavaVirtualMachines or ~/Library/Java/JavaVirtualMachines.  A
# Homebrew JDK is keg-only and lands in neither, so `clojure` fails with
# "Unable to locate a Java Runtime" even though a JDK is installed.  Fall back
# to the Homebrew location when the shell cannot run java itself.

ifeq ($(shell java -version >/dev/null 2>&1 && echo ok),)
  JAVA_HOME := $(firstword $(wildcard /opt/homebrew/opt/openjdk/libexec/openjdk.jdk/Contents/Home \
                                      /usr/local/opt/openjdk/libexec/openjdk.jdk/Contents/Home))
  export JAVA_HOME
  export PATH := $(JAVA_HOME)/bin:$(PATH)
endif

.PHONY: test check mcp cli repl clean

## Run the whole suite (BDD scenarios, unit, MCP protocol, performance).
test:
	clojure -M:test

check: test

## Start the MCP server on stdio, as an MCP client would.
mcp:
	clojure -M:mcp

## Ad-hoc command line access to the same tools, e.g. `make cli ARGS="standings --season 2019"`.
cli:
	clojure -M:cli $(ARGS)

repl:
	clojure -M:test -r

clean:
	rm -rf .cpcache target
