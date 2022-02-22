FROM python:3-alpine

# Upgrade expat fixing https://nvd.nist.gov/vuln/detail/CVE-2022-23852 , https://nvd.nist.gov/vuln/detail/CVE-2022-23990
# Upgrade libuuid fixing https://nvd.nist.gov/vuln/detail/CVE-2021-3995 , https://nvd.nist.gov/vuln/detail/CVE-2021-3996 , https://nvd.nist.gov/vuln/detail/CVE-2022-0563
RUN apk upgrade --no-cache

COPY ./requirements.txt requirements.txt

# install python deps
RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt

# copy and run entrypoint
COPY ./index-records.py /index-records.py

ENTRYPOINT ["python", "/index-records.py"]
