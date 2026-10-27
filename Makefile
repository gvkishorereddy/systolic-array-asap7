PYTHON ?= python3
JOBS ?= 4
.PHONY: test physical collect
test:
	$(PYTHON) scripts/verify.py
physical:
	$(PYTHON) scripts/run_asap7.py --target all --jobs $(JOBS)
collect:
	$(PYTHON) scripts/collect_evidence.py
