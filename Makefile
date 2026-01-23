PYTHON ?= python3

.PHONY: test install help

help:
	@echo "Targets:"
	@echo "  make test      - run unit tests"
	@echo "  make install   - print installation guidance"
	@echo "  make help      - this help"

test:
	@PYTHONPATH="$(CURDIR)/src" "$(PYTHON)" -m unittest discover -s tests/unit -p "test_*.py" -v

install:
	sudo pip install -e . --upgrade --break-system-packages
