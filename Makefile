PY ?= python3

.PHONY: test install help

help:
	@echo "Targets:"
	@echo "  make test      - run unit tests"
	@echo "  make install   - print installation guidance"
	@echo "  make help      - this help"

test:
	$(PY) -m unittest -v test.py

install:
	@echo "Installation is provided via your package manager:"
	@echo "  pkgmgr install automtu"
	@echo ""
	@echo "Alternatively, run the tool directly:"
	@echo "  $(PY) main.py [--options]"
