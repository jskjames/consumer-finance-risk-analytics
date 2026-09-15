PYTHON ?= python
RUN = PYTHONPATH=src $(PYTHON)

.PHONY: setup download build analyze model report app test all

setup:
	$(PYTHON) -m pip install -r requirements.txt

download:
	$(RUN) -m cfri.download

build:
	$(RUN) -m cfri.pipeline

analyze:
	$(RUN) -m cfri.analytics

model:
	$(RUN) -m cfri.model

report:
	$(RUN) -m cfri.reporting

app:
	streamlit run app.py

test:
	$(RUN) -m unittest discover -s tests -v

all: download build analyze model report
