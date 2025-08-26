#!/usr/bin/env node

/**
 * SUMMARY
 *
 * derive a semver-compatible value from ./package.json's version and the build-number
 *
 *
 * USAGE
 *
 * JOB_ID=123 ./$0              // output like 11.1.109000000123
 * JOB_ID=1234 ./$0             // output like 11.1.109000001234
 * JOB_ID=123 new_ci=true ./$0  // output like 11.1.10990000000123
 * JOB_ID=1234 new_ci=true ./$0 // output like 11.1.10990000001234
 *
 *
 * DETAILS
 *
 * Given package.json contains a version value like `1.2.0` or `2.3.4` and
 * the environment variable JOB_ID contains a build-number like 456, concoct
 * a version number like `1.2.109000000456` or `2.3.409000000456` and print it.
 *
 * When the environment variable new_ci is truthy, the generated patch value
 * is padded to 14-16 places with a prefix of ${patch}099. Otherwise, the
 * generated patch value is padded to 12-14 places with a prefix of ${patch}09.
 *
 * Exits 0 on success, 2 if package.json is not found, and 3 in case of any
 * other error.
 *
 * The max patch value from package.json is 900.
 *
 * The max JOB_ID is 9_999_999_999 when new_ci is true, 999_999_999 without it.
 *
 * Why oh why do we do it this way? A long time ago, on a Jenkins server far
 * far away, tacking the build-number onto the patch-version was chosen as a
 * quick way to create incremental builds when making a commit to master and
 * auto-publishing this resulting build as a new version to the CI server.
 * After a server migration, build-numbers restarted at 1, wreaking havoc with
 * this scheme since new builds were generating semantically lower versions,
 * hence the introduction of `new_ci`. We ... messed up a few times, hence the
 * padding with 09, or 099
 *
 * Point of interest, or maybe disinterest: the max JOB_ID and patch values
 * derive from needing to keep the final value below  2^53 -1,
 * 9_007_199_254_740_991, the maximum value as of npm 10.9.2. This script was
 * written to replace the old bash script which simply concatenated the
 * build-number onto the end instead of padding to a constant width, causing
 * grief with a patch value of 9 and a build-number greater than 999:
 *   yarn version --new-version 11.0.9099000000001021
 *   error Invalid version supplied.
 *
 *
 */
const main = ({ buildId, newCi }) => {
  try {
    const pkg = require(`${process.env.PWD}/package.json`);
    if (!pkg) {
      console.error("package.json file not found");
      process.exit(2);
    }

    const buildNumber = Number.parseInt(buildId, 10);
    if (!buildNumber) {
      throw new Error(`could not parse buildId: '${buildId}'`)
    }
    const isNewCi = !!newCi;

    // from https://semver.org/
    const regex = /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$/;
    const [ver, vmajor, vminor, vpatch] = pkg.version.match(regex);

    const patchNumber = Number.parseInt(vpatch, 10);
    if (patchNumber && patchNumber > 900) {
      throw new Error(`patch number cannot exceed 900 ('${vpatch}')`)
    }

    // patch must parse as a number, i.e. can be 0 but not start with 0.
    const patch = (vpatch === "0") ? "1" : vpatch;
    const snapshot = `${vmajor}.${vminor}.${patch}`;

    // padding is a constant width based on the magnitude of buildNumber
    // repeat() will throw if magnitude is too great, resulting in < 0
    const magnitude = Math.floor(Math.log10(buildNumber));
    const pad = isNewCi ? `099${'0'.repeat(9 - magnitude)}` : `09${'0'.repeat(8 - magnitude)}`;

    return `${snapshot}${pad}${buildNumber}`

  } catch (e) {
    if (e.message.startsWith('Cannot find module')) {
      console.error('package.json file not found')
      process.exit(2);
    }
    console.error(e.message);
    process.exit(3);
  }
}

const version = main({ buildId: process.env.JOB_ID, newCi: process.env.new_ci });
console.log(version);

