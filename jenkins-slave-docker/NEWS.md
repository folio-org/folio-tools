## 3.0.1 java-17 2022-07-01

* Upgrade Docker to 20.10.17
* Upgrade Yarn to 1.22.19
* Upgrade Nodejs to 16.15.1
* Upgrade Google Chrome to 103.0.5060.53
* Upgrade api-lint FOLIO-3528

## 2.10.1 java-11 2022-07-01

* Upgrade Docker to 20.10.17
* Upgrade Yarn to 1.22.19
* Upgrade Nodejs to 14.19.3
* Upgrade Google Chrome to 103.0.5060.53
* Upgrade api-lint FOLIO-3528

## 2.10.0 java-11 2022-05-17

* Upgrade "java-11" image from 20.04 Focal to 22.04 Jammy [FOLIO-3478](https://issues.folio.org/browse/FOLIO-3478)
* Remove firefox [FOLIO-3478](https://issues.folio.org/browse/FOLIO-3478)
* Still Node v14.

## 3.0.0 java-17 2022-05-12

* Build "java-17" image from Dockerfile.jammy-java-17 [FOLIO-3494](https://issues.folio.org/browse/FOLIO-3494)
* Use Ubuntu 22.04 LTS (Jammy Jellyfish) [FOLIO-3478](https://issues.folio.org/browse/FOLIO-3478)
* Use OpenJDK 17.0.3
* Use NodeJS LTS v16 (16.15.0) [FOLIO-3434](https://issues.folio.org/browse/FOLIO-3434)

## 2.9.6 2022-05-10

* Update api-lint FOLIO-3486

## 2.9.5 2022-05-03

* Upgrade Docker to 20.10.14
* Upgrade Yarn to 1.22.18
* Upgrade Ansible to 2.9.27
* Upgrade OpenJDK to 11.0.15 FOLIO-3464
* Upgrade Google Chrome to 101.0.4951.54

## 2.9.4 2022-01-21

* Update Linux base FOLIO-3397

## 2.9.3 2022-01-13

* Remove global installation of stripes-cli from image
* Upgrade yarn to 1.22.17 (from 1.22.15).

## 2.9.2 2022-01-12

* Update api-lint FOLIO-3382
* The re-build also updated some other important tools:
  * Google Chrome 97.0.4692.71
  * stripes 2.5.10000018

## 2.9.1 2021-12-14

* Upgrade Node to v14 (14.18.2) FOLIO-3352
* Upgrade Yarn (1.22.15) FOLIO-3353
* Upgrade Docker (20.10.11) FOLIO-3353
* The re-build also updates other important tools:
  * Google Chrome 96.0.4664.93
  * ansible 2.9.23
  * aws-cli 2.4.6
  * stripes 2.4.1000005

## 2.9.0 2021-07-07

* Remove Dockerfile.agent-focal-java-11 and Dockerfile.xenial-java-8. They are not maintained and shouldn't been used any longer.
* Remove Ruby, no longer needed. Ruby 2.4 has multiple vulnerabilities. Solves https://issues.folio.org/browse/FOLIO-3164
* Update PostgreSQL from 10 to 12. Solves https://issues.folio.org/browse/FOLIO-3167
* Update Docker from 20.10.6 to 20.10.7.
* Update Ansible from 2.9.21 to 2.9.23.

* The re-build also updates many other important tools:

* Update Node from 12.22.1 to 12.22.2 ( https://nodejs.org/en/blog/release/v12.22.2/ ) fixing
  * CVE-2021-27290: npm upgrade - ssri Regular Expression Denial of Service (ReDoS) (High)
  * CVE-2021-22918: libuv upgrade - Out of bounds read (Medium)
  * CVE-2021-22921: Windows installer - Node Installer Local Privilege Escalation (Medium)
  * CVE-2021-23362: npm upgrade - hosted-git-info Regular Expression Denial of Service (ReDoS) (Medium)
* Google Chrome 91.0.4472.114 - https://chromereleases.googleblog.com/search/label/Stable%20updates
  * Critical CVE-2021-30544: Use after free in BFCache.
  * High CVE-2021-30521: Heap buffer overflow in Autofill.
  * High CVE-2021-30522: Use after free in WebAudio.
  * High CVE-2021-30523: Use after free in WebRTC.
  * High CVE-2021-30524: Use after free in TabStrip.
  * High CVE-2021-30525: Use after free in TabGroups.
  * High CVE-2021-30526: Out of bounds write in TabStrip.
  * High CVE-2021-30527: Use after free in WebUI.
  * High CVE-2021-30528: Use after free in WebAuthentication.
  * High CVE-2021-30545: Use after free in Extensions.
  * High CVE-2021-30546: Use after free in Autofill.
  * High CVE-2021-30547: Out of bounds write in ANGLE.
  * High CVE-2021-30548: Use after free in Loader.
  * High CVE-2021-30549: Use after free in Spell check.
  * High CVE-2021-30550: Use after free in Accessibility.
  * High CVE-2021-30551: Type Confusion in V8.
  * High CVE-2021-30554: Use after free in WebGL
  * High CVE-2021-30555: Use after free in Sharing.
  * High CVE-2021-30556: Use after free in WebAudio.
  * High CVE-2021-30557: Use after free in TabGroups.
  * Medium CVE-2021-30529: Use after free in Bookmarks.
  * Medium CVE-2021-30530: Out of bounds memory access in WebAudio.
  * Medium CVE-2021-30531: Insufficient policy enforcement in Content Security Policy.
  * Medium CVE-2021-30532: Insufficient policy enforcement in Content Security Policy.
  * Medium CVE-2021-30533: Insufficient policy enforcement in PopupBlocker.
  * Medium CVE-2021-30534: Insufficient policy enforcement in iFrameSandbox.
  * Medium CVE-2021-30535: Double free in ICU.
  * Medium CVE-2021-30542: Use after free in Tab Strip
  * Medium CVE-2021-30543: Use after free in Tab Strip.
  * Medium CVE-2021-30558: Insufficient policy enforcement in content security policy.
  * Medium CVE-2021-30552: Use after free in Extensions.
  * Medium CVE-2021-30553: Use after free in Network service.
  * Low CVE-2021-30536: Out of bounds read in V8.
  * Low CVE-2021-30537: Insufficient policy enforcement in cookies.
  * Low CVE-2021-30537: Insufficient policy enforcement in cookies.
  * Low CVE-2021-30539: Insufficient policy enforcement in content security policy.
  * Low CVE-2021-30540: Incorrect security UI in payments.
* aws-cli/2.2.17
* stripes-cli 2.3.1000253


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
