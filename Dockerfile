FROM python:3.14

ENV TZ=America/Los_Angeles

# install required packages
RUN --mount=type=bind,source=requirements.txt,target=/tmp/requirements.txt \
   pip install --requirement /tmp/requirements.txt

COPY . /app
WORKDIR /app

CMD ["python3", "-u", "./bot.py"]
