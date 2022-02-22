FROM python:3-alpine

# Upgrade expat fixing https://nvd.nist.gov/vuln/detail/CVE-2022-23852 , https://nvd.nist.gov/vuln/detail/CVE-2022-23990
# Upgrade libuuid fixing https://nvd.nist.gov/vuln/detail/CVE-2021-3995 , https://nvd.nist.gov/vuln/detail/CVE-2021-3996 , https://nvd.nist.gov/vuln/detail/CVE-2022-0563
RUN apk upgrade --no-cache

# install python deps
RUN pip3 install --upgrade pip
RUN pip3 install argparse \
  jinja2 \
  requests

# copy in build context
COPY . .

ENTRYPOINT ["python", "/md2kubeyaml.py"]
