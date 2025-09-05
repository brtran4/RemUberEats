install:
	pip3 install -r requirements.txt

start:
	docker compose up python-app --build

stop:
	docker compose down

clean:
	docker image prune -a

.PHONY: install start stop clean
