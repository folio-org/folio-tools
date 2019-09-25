FROM python:3-alpine

# install python deps
RUN pip3 install --upgrade pip
RUN pip3 install argparse \
  jinja2 \
  requests

# copy in build context
COPY . .

ENTRYPOINT ["python", "/md2kubeyaml.py"]
