FROM python:3-alpine

# install python deps
RUN pip3 install --upgrade pip
RUN pip3 install argparse \
  kubernetes \
  requests

# copy and run entrypoint
COPY ./kube-cleanup.py /kube-cleanup.py

ENTRYPOINT ["python", "/kube-cleanup.py"]
