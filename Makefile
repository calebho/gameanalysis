PYTEST_ARGS = -n auto --strict --showlocals

help: temp
	@echo "usage: make <tag>"
	@echo
	@echo "update   - get environment ready to run and verify up to date"
	@echo "test     - run the tests, add file=<file> to run on a specific file e.g. file=rsgame"
	@echo "big      - run all of the tests (may fail on some computers)"
	@echo "coverage - run the tests and print coverage, add file=<file> to run on specific file"
	@echo "check    - check code for style"
	@echo "todo     - list all XXX, TODO and FIXME flags"
	@echo "minor    - commit a minor version"
	@echo "major    - commit a major version"
	@echo "ubuntu-reqs - install necessary packages on ubuntu (requires root)"

test:
ifdef file
	bin/py.test test/$(file)_test.py $(PYTEST_ARGS)
else
	bin/py.test test $(PYTEST_ARGS)
endif

coverage:
ifeq ($(file),scripts)
	bin/py.test test/$(file)_test.py $(PYTEST_ARGS) --cov gameanalysis/$(file) --cov test/$(file)_test.py --cov-report term-missing
else
ifdef file
	bin/py.test test/$(file)_test.py $(PYTEST_ARGS) --cov gameanalysis/$(file).py --cov test/$(file)_test.py --cov-report term-missing
else
	bin/py.test test $(PYTEST_ARGS) --cov gameanalysis --cov test --cov-report term-missing
endif
endif

big: export BIG_TESTS=ON
big: test

check:
	bin/flake8 gameanalysis test

format:
	bin/autopep8 -ri gameanalysis test

todo:
	grep -nrIF -e TODO -e XXX -e FIXME . --exclude-dir=.git --exclude-dir=lib --exclude=Makefile --color=always

setup:
	pyvenv .
	bin/pip install -U pip setuptools
	bin/pip install -e .
	bin/pip install -r requirements.txt

ubuntu-reqs:
	sudo apt-get install python3 libatlas-base-dev gfortran python3-venv moreutils jq

bump-minor:
	jq '.version = (.version | split(".") | .[1] = (.[1] | tonumber + 1 | tostring) | join("."))' setup.json | sponge setup.json

bump-major:
	jq '.version = (.version | split(".") | [.[0] | tonumber + 1 | tostring, "0"] | join("."))' setup.json | sponge setup.json

bump-sync:
	git commit setup.json
	git tag v$(shell jq .version setup.json)
	git push $(shell git remote | head -n1) v$(shell jq .version setup.json)

minor: bump-minor bump-sync

major: bump-major bump-sync

clean:
	rm -rf bin include lib lib64 share

.PHONY: test big
