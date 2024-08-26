## 3.0.0 2024-...
* Initial version for Java 21
* No libc6-compat for OpenSSL because OpenJDK 21 ships with fast implementations of TLSv1.3 and TLSv1.2
  making OpenSSL useless. Modules that still want to use OpenSSL can easily add libc6-compat.
