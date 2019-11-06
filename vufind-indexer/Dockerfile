FROM python:3-alpine

COPY ./requirements.txt requirements.txt

# install python deps
RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt

# copy and run entrypoint
COPY ./index-records.py /index-records.py

ENTRYPOINT ["python", "/index-records.py"]
