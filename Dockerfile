FROM python:3.14

ENV TZ=America/Los_Angeles

# install required packages
RUN --mount=type=bind,source=requirements.txt,target=/tmp/requirements.txt \
   pip install --requirement /tmp/requirements.txt

COPY . /opt/app
WORKDIR /opt/app

CMD ["python3", "./bot.py"]
