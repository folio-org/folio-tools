FROM python:3-alpine

COPY ./requirements.txt requirements.txt

# install python deps
RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt

# copy and run entrypoint
COPY ./kube-cleanup.py /kube-cleanup.py

ENTRYPOINT ["python", "/kube-cleanup.py"]
