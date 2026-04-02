install:
	pip3 install -r requirements.txt

start:
	docker compose up -d --build python-app

stop:
	docker compose down

clean:
	docker image prune -a

test:
	docker run --rm -v $$(pwd):/app -w /app rem-uber-eats-python-app pytest tests/ -v

.PHONY: install start stop clean test
