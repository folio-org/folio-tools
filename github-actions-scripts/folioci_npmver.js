#!/usr/bin/env node

/**
 * SUMMARY
 *
 * derive a semver-compatible value from ./package.json's version and the build-number
 *
 * USAGE
 *
 * JOB_ID=123 ./$0              // output like 11.1.10900000000123
 * JOB_ID=1234 ./$0             // output like 11.1.10900000001234
 * JOB_ID=123 new_ci=true ./$0  // output like 11.1.1099000000000123
 * JOB_ID=1234 new_ci=true ./$0 // output like 11.1.1099000000001234
 *
 * DETAILS
 *
 * WARNING: LARK'S VOMIT
 *
 * There are so many shenanigans here. Really, this whole script is one big
 * shenanigan. See below for the history of how we dug this pit, but don't
 * think ill of anybody who was just trying to do the smallest, quickest thing
 * possible to enable devs to get on with their work. Why are we publishing
 * 11.1.1099000000001234 instead of 11.1.0-snapshot.1234? Because we are. It
 * started as a simple scheme a long time ago and now a lot of infrastructure
 * leans on the conventions we accidentally established. In other words, it
 * is simply how things work at present. Just accept it.
 *
 * OK, on with the show.
 *
 * Given package.json contains a version value like `2.3.4` and the environment
 * variable JOB_ID contains a build-number like 456, concoct a version number
 * `2.3.4090000000000456` and print it. The patch value will be either 14 or 16
 * characters depending on the input. The formula is
 *
 *   patch-prefix-padding-build
 *
 * where:
 * * patch is the input patch number from ./package.json::version
 * * prefix is 099, 09, or 9
 * * padding is 0 or more 0s
 * * build is the value from process.env.JOB_ID
 *
 * input notes:
 * * package.json's patch-value must be < 90, != 9
 * * JOB_ID must be < 999_999_999_999
 * * when new_ci is falsey, patch values are padded to 14 characters
 * * when new_ci is truthy, patch values are padded to 16 characters
 *
 * Yes, this means we could allow larger build numbers when new_ci is falsey,
 * but we don't. This script is already complicated enough.
 *
 * Exits 0 on success, 2 if package.json is not found, and 3 in case of any
 * other error.
 *
 * GORY DETAILS, CRUNCHY FROGS, AND EXPLODING STEEL BOLTS
 *
 * Why oh why do we do it this way? A long time ago, on a Jenkins server far
 * far away, tacking the build-number onto the patch-version was chosen as a
 * quick way to create incremental builds when making a commit to master and
 * auto-publishing this resulting build as a new version to the CI server.
 * After a server migration, build-numbers restarted at 1, wreaking havoc with
 * this scheme since new builds were generating semantically lower versions,
 * hence the introduction of `new_ci`. We ... messed up a few times, hence the
 * padding with 09, or 099.
 *
 * Point of interest, or maybe disinterest: the max JOB_ID and patch values
 * derive from needing to keep the final value below  2^53 -1,
 * 9_007_199_254_740_991, the maximum value as of npm 10.9.2. This script was
 * written to replace the old bash script which simply concatenated the
 * build-number onto the end instead of padding to a constant width, causing
 * grief with a patch value of 9 and a build-number greater than 999:
 *   yarn version --new-version 11.0.9099000000001021
 *   error Invalid version supplied.
 * So we have this situation:
 *   9_007_199_254_740_991 // max value
 *   P_099_BBB_BBB_BBB_BBB // P == patch values < 9, B == build numbers
 *   P_P99_BBB_BBB_BBB_BBB // PP == patch values > 9, B == build numbers
 * which is why we accept values for P of 1-8 and 10-89, but not 9.
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
    if (!Number.isInteger(buildNumber)) {
      throw new Error(`JOB_ID is not an integer: '${buildId}'`)
    }
    const isNewCi = !!newCi;

    // it's tempting to think a smaller, simpler regex would be sufficient
    // here, but since semver org suggests a regex, we'll accept the offer.
    // from https://semver.org/#is-there-a-suggested-regular-expression-regex-to-check-a-semver-string
    const regex = /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$/;
    const [ver, vmajor, vminor, vpatch] = pkg.version.match(regex);

    const patchNumber = Number.parseInt(vpatch, 10);
    // new_ci lpad is 1-3 characters
    if (patchNumber && patchNumber > 89) {
      throw new Error(`patch number cannot exceed 89 ('${vpatch}')`)
    }

    // patch-number cannot be 9 because 9_099_BBB_BBB_BBB_BBB > 9_007_199_254_740_991
    if (patchNumber && patchNumber === 9) {
      throw new Error(`bwahahaha patch number cannot be 9 ('${vpatch}')`)
    }

    // patch must parse as a number, i.e. can be 0 but not start with 0.
    // that is, even though we treat it like a string here and tack
    // values onto the end, the result needs to be parseable as a number, and
    // thus cannot start with 0. the simple hack here is to convert 0 to 1,
    // meaning input like `1.2.0` provides output like `1.2.109000000123`.
    // treating 0 and 1 the same might seem problematic, but we don't have to
    // worry about collisions because the build-numbers we tack on at the end
    // always increase, leading to unique values.
    const patch = (vpatch === "0") ? "1" : vpatch;
    const snapshot = `${vmajor}.${vminor}.${patch}`;

    // pad to a constant width based on the magnitude of buildNumber.
    // repeat(n) will throw given n < 0, i.e. if magnitude is too great
    const magnitude = Math.floor(Math.log10(buildNumber));

    const lpad = patchNumber > 9 ? '9' : '09';
    const rpad = isNewCi ? `9${'0'.repeat(11 - magnitude)}` : `${'0'.repeat(9 - magnitude)}`;

    return `${snapshot}${lpad}${rpad}${buildNumber}`

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

