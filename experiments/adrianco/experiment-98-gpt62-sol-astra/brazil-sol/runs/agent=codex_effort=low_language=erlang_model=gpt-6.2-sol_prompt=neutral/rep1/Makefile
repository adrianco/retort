ERLC ?= erlc
ERL ?= erl
BUILD := _build
MODULES := soccer_data soccer_query soccer_mcp

.PHONY: all run test clean
all: $(MODULES:%=$(BUILD)/%.beam) $(BUILD)/soccer-mcp

$(BUILD):
	mkdir -p $@

$(BUILD)/%.beam: %.erl | $(BUILD)
	$(ERLC) -Werror -o $(BUILD) $<

$(BUILD)/soccer-mcp: $(MODULES:%=$(BUILD)/%.beam)
	$(ERL) -noshell -eval 'ok = escript:create("$@", [shebang, {emu_args, "-escript main soccer_mcp"}, {archive, ["soccer_data.beam","soccer_query.beam","soccer_mcp.beam"], [{cwd,"$(BUILD)"}]}]), halt().'
	chmod +x $@

run: all
	@$(BUILD)/soccer-mcp "$(CURDIR)/data/kaggle"

test: all $(BUILD)/soccer_tests.beam
	$(ERL) -noshell -pa $(BUILD) -eval 'case eunit:test(soccer_tests, [verbose]) of ok -> halt(0); error -> halt(1) end.'

clean:
	rm -rf $(BUILD)
