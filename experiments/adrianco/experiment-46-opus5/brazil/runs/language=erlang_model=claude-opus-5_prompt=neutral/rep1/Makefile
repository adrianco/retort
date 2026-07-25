.PHONY: all compile escript test check clean shell summary dialyzer

all: compile escript

compile:
	rebar3 compile

## builds _build/default/bin/bsmcp, the executable an MCP client launches
escript:
	rebar3 escriptize

## the stdio transport suite drives the executable, so build it first
test: escript
	rebar3 ct

check: test dialyzer

dialyzer:
	rebar3 dialyzer

shell:
	rebar3 shell

summary: escript
	./_build/default/bin/bsmcp summary

clean:
	rebar3 clean
	rm -rf _build/test/logs
