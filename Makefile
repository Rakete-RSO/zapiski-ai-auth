.PHONY: format lint sort all

all: format lint sort

format:
	poetry run black src/

lint:
	poetry run flake8 src/

sort:
	poetry run isort src/
