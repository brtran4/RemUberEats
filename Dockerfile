FROM python:3.12

# install required packages
RUN --mount=type=bind,source=requirements.txt,target=/tmp/requirements.txt \
   pip install --requirement /tmp/requirements.txt

COPY . /opt/app
WORKDIR /opt/app

CMD ["python3", "./bot.py"]
