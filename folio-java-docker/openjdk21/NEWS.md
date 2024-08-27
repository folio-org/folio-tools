## 3.0.0 2024-08-27

* Initial version for Java 21
* Uses eclipse-temurin:21-jre-alpine latest [FOLIO-4048](https://folio-org.atlassian.net/browse/FOLIO-4048)
* OpenJDK Runtime Environment Temurin-21.0.4+7
* No libc6-compat for OpenSSL because OpenJDK 21 ships with fast implementations of TLSv1.3 and TLSv1.2
  making OpenSSL useless. Modules that still want to use OpenSSL can easily add libc6-compat (refer to our README.md).
