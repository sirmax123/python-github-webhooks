FROM python:2.7-alpine
MAINTAINER "Matjaž Finžgar" <matjaz@finzgar.net>

WORKDIR /app

#ADD some-new-CA.pem /usr/local/share/ca-certificates/some-new-CA.crt
#RUN update-ca-certificates

COPY requirements.txt /app
RUN pip install -r requirements.txt

COPY . /app

EXPOSE 5000
CMD ["python", "webhooks.py"]
