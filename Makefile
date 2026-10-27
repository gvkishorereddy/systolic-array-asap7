PYTHON ?= python3
JOBS ?= 4
ELAB_FLAGS ?=
.PHONY: test elaborate physical collect
test:
	$(PYTHON) scripts/verify.py
elaborate:
	$(PYTHON) scripts/elaborate.py $(ELAB_FLAGS)
physical:
	$(PYTHON) scripts/run_asap7.py --target all --jobs $(JOBS)
collect:
	$(PYTHON) scripts/collect_evidence.py
