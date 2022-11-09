## 2.0.5 2022-11-08

* Rebuild to update [FOLIO-3611](https://issues.folio.org/browse/FOLIO-3611)
* OpenJDK Runtime Environment Temurin-17.0.5+8

## 2.0.4 2022-10-11

* Rebuild to update [FOLIO-3552](https://issues.folio.org/browse/FOLIO-3552)
* OpenJDK Runtime Environment Temurin-17.0.4.1+1

## 2.0.3 2022-08-08

* Rebuild to update [FOLIO-3544](https://issues.folio.org/browse/FOLIO-3544)
* OpenJDK Runtime Environment Temurin-17.0.4+8

## 2.0.2 2022-06-28

* Rebuild to update [FOLIO-3529](https://issues.folio.org/browse/FOLIO-3529)
* Upgraded to eclipse-temurin:17-jre-alpine latest (using Alpine 3.16)

## 2.0.1 2022-05-18

* Remove curl. Use wget for module docker health check [FOLIO-3507](https://issues.folio.org/browse/FOLIO-3507)

## 2.0.0 2022-05-12

* Initial version.
* Uses eclipse-temurin:17-jre-alpine latest [FOLIO-3499](https://issues.folio.org/browse/FOLIO-3499)
* Specifically uses zlib-1.2.12-r1 ZipException [FOLIO-3487](https://issues.folio.org/browse/FOLIO-3487)
  as not yet in eclipse-temurin:17-jre-alpine
* Uses fabric8io-images run-java.sh [3a9b65a](https://github.com/fabric8io-images/java/blob/3a9b65a4b6cad3a324d313b84aa34d42a1437034/images/alpine/openjdk11/jre/run-java.sh)
