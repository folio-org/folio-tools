FROM python:3-alpine

# Upgrade expat fixing https://nvd.nist.gov/vuln/detail/CVE-2022-23852 , https://nvd.nist.gov/vuln/detail/CVE-2022-23990
# Upgrade libuuid fixing https://nvd.nist.gov/vuln/detail/CVE-2021-3995 , https://nvd.nist.gov/vuln/detail/CVE-2021-3996 , https://nvd.nist.gov/vuln/detail/CVE-2022-0563
RUN apk upgrade --no-cache

ENV CLEANUP_OKAPI="http://okapi:9130"
ENV CLEANUP_ORGANIZATION="folio-org"
ENV CLEANUP_GH_TOKEN=""
ENV CLEANUP_OKAPI_USER="okapi_default_admin"
ENV CLEANUP_OKAPI_PASSWORD=""
ENV CLEANUP_TENANT="supertenant"
ENV CLEANUP_AWS_KEY_ID=""
ENV CLEANUP_AWS_SECRET=""

# install python deps
RUN pip3 install --upgrade pip
RUN pip3 install boto3 \
  requests

# copy and run entrypoint
COPY ./tenant-cleanup.py /tenant-cleanup.py

CMD ["python", "/tenant-cleanup.py"]
