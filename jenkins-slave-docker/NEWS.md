## 2.8.2 2021-05-17

* Update Ansible from 2.9.13 to 2.9.21 fixing security issues:
  * https://access.redhat.com/security/cve/cve-2021-2022 - Mask default and fallback values for `no_log` module options
  * https://access.redhat.com/security/cve/cve-2021-20191 - Various modules missing `no_log` on sensitive module arguments
  * https://access.redhat.com/security/cve/cve-2021-20180 - `bitbucket_pipeline_variable` - hide user sensitive information which are marked as `secured` from logging into the console
  * https://access.redhat.com/security/cve/cve-2021-20178 - `snmp_facts` - hide user sensitive information such as ``privkey`` and ``authkey`` from logging into the console
  * https://access.redhat.com/security/cve/cve-2020-1753 - kubectl connection plugin - now redacts `kubectl_token` and `kubectl_password` in console log

* Update Docker from 19.03.9 to 20.10.6 fixing
  * CVE-2021-21285 Prevent an invalid image from crashing docker daemon https://github.com/moby/moby/security/advisories/GHSA-6fj5-m822-rqx8
  * CVE-2021-21284 Lock down file permissions to prevent remapped root from accessing docker state https://github.com/moby/moby/security/advisories/GHSA-7452-xqpj-6rpc
  * CVE-2019-14271 loading of nsswitch based config inside chroot under Glibc https://github.com/moby/moby/pull/39612
  * CVE-2020-15257 Update bundled static binaries of containerd to v1.3.9 https://github.com/containerd/containerd/security/advisories/GHSA-36xw-fx78-c5r4

* Update Yarn from 1.22.4 to 1.22.5, to the classic stable version: https://classic.yarnpkg.com/lang/en/

* The re-build also updates many other tools, most notably Node:

* Update Node from 12.20.1 to 12.22.1 fixing
  * https://nodejs.org/en/blog/vulnerability/april-2021-security-releases/ OpenSSL - CA certificate check bypass with `X509_V_FLAG_X509_STRICT` (CVE-2021-3450)
  * https://nodejs.org/en/blog/vulnerability/april-2021-security-releases/ OpenSSL - NULL pointer deref in signature_algorithms processing (CVE-2021-3449)
  * https://nodejs.org/en/blog/vulnerability/april-2021-security-releases/ npm upgrade - Update y18n to fix Prototype-Pollution (CVE-2020-7774)
  * https://nodejs.org/en/blog/vulnerability/february-2021-security-releases/ HTTP2 'unknownProtocol' cause Denial of Service by resource exhaustion (CVE-2021-22883)
  * https://nodejs.org/en/blog/vulnerability/february-2021-security-releases/ DNS rebinding in --inspect (CVE-2021-22884)
  * https://nodejs.org/en/blog/vulnerability/february-2021-security-releases/ OpenSSL - Integer overflow in CipherUpdate (CVE-2021-23840)

* openjdk version "11.0.11"
* Google Chrome 90.0.4430.212
* aws-cli/2.2.5
* stripes 2.2.1000249

## 2.8.1 2021-04-19

* Update api-doc FOLIO-2898
* Update api-lint FOLIO-2893
* Update api-schema-lint FOLIO-2917
* The re-build also updated some other important tools:
  * Google Chrome 90.0.4430.72
  * stripes 2.2.1000248

## 2.8.0 2021-03-15

* Add api-doc FOLIO-2898
* The re-build also updated some other important tools:
  * Google Chrome 89.0.4389
  * stripes 2.0.1000246

## 2.7.1 2021-02-05

* Update api-schema-lint FOLIO-2917
* The re-build also updated some other important tools:
  * Google Chrome 88.0.4324 (was 87.0.4280)
  * stripes 2.0.1000244 (was 1.20.1000236)

## 2.7.0 2021-01-13

* Add api-schema-lint FOLIO-2917

## 2.6.1 2021-01-05

* Rebuild image to upgrade Node (now 12.20.1 was 12.20.0) fixing
  TLS, HTTP and OpenSSL security vulnerabilities (CVE-2020-8265, CVE-2020-8287, CVE-2020-1971)
  https://issues.folio.org/browse/STCOR-497

## 2.6.0 2020-12-29

* add libyaz5 FOLIO-2925

## 2.5.0 2020-12-18

* Fix wget FOLIO-2923

## 2.4.0 2020-12-09

* Add api-lint FOLIO-2893

## 2.3.2 2020-11-06

* add libraries for building LDP

## 2.3.1 2020-11-03

* Java 11

## 2.3.0 2020-11-03

* Java 11

## 2.2.0 2020-09-04

* Java 11

## 2.1.0 2020-08-15

* Java 11

## 1.2.2 latest 2020-04-30

* Java 8
* Deprecated: This is the final of the 1.x series.

## 1.2.1 2020-04-24

* Utilise new stripes-cli v1.15.1 FOLIO-2572,STCLI-148

## 1.2.0 2020-04-14

* Upgrade Node to v12 (now v12.16.2 was v10.17.0)
* Upgrade Yarn (now v1.22.4 was v1.15.2)

## 1.1.0 2019-12-12

* Upgrade Node to v10.17.0
* Use pip instead of ppa to install ansible, pin to version 2.7.5

## 1.0.0

* Existing "latest" tag as of 2019-12-11 (uses node 8)
