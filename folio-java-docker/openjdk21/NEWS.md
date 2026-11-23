## 4.0.0 2026-11-23

* Uses eclipse-temurin:21-jre-alpine latest 3.24
* OpenJDK Runtime Environment Temurin-21.0.13.1+2-LTS
* New run-java.sh.  The new script keeps the original's JAVA_APP_JAR resolution (auto-detect, bare-name search, absolute path, original-* filtering, JAR/WAR) and its JAVA_OPTIONS pass-through, but replaces all the shell-based cgroup v1 memory/CPU/GC math with a single -XX:MaxRAMPercentage (default 50%), trusting OpenJDK 17+ to read cgroup v1/v2 limits natively. It also drops the extras — JAVA_MAIN_CLASS/classpath mode, the sub-300 MB 25% step-down, and the GC/JIT/CPU/debug/proxy tuning.

## 3.2.0 2026-11-03

* Uses eclipse-temurin:21-jre-alpine latest 3.24 [FOLIO-4588](https://folio-org.atlassian.net/browse/FOLIO-4588)
* OpenJDK Runtime Environment Temurin-21.0.13+9

## 3.1.0 2025-08-05

* Uses eclipse-temurin:21-jre-alpine latest 3.22 [FOLIO-4243](https://folio-org.atlassian.net/browse/FOLIO-4243)
* OpenJDK Runtime Environment Temurin-21.0.8+9

## 3.0.0 2024-08-27

* Initial version for Java 21
* Uses eclipse-temurin:21-jre-alpine latest [FOLIO-4048](https://folio-org.atlassian.net/browse/FOLIO-4048)
* OpenJDK Runtime Environment Temurin-21.0.4+7
* No libc6-compat for OpenSSL because OpenJDK 21 ships with fast implementations of TLSv1.3 and TLSv1.2
  making OpenSSL useless. Modules that still want to use OpenSSL can easily add libc6-compat (refer to our README.md).
