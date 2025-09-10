#!/usr/bin/env node

import { after, before, describe, it } from 'node:test';
import assert from 'node:assert';
import process from 'node:process';
import { execFileSync } from 'node:child_process';
import { open, close, fstat, writeFileSync, unlinkSync } from 'node:fs';

const version = (v, jid, newCi = false) => {
  try {
    writeFileSync('./package.json', `{ "version": "${v}" }`);

    const stdout = execFileSync('./folioci_npmver.js', [], {
      env: { ...process.env, JOB_ID: jid, ...(newCi && { new_ci: true }) },
    });

    return stdout.toString().trim();
  } catch (err) {
    // could not run the process
    if (err.code) {
      console.error({ code: err.code });
    }
    // ran the process but it exited non-zero
    else {
      // throw stderr in an error
      // yep, sorry, we lose the exit code
      const { stdout, stderr } = err;
      throw new Error(stderr);
    }
  }
}

describe('folioci_npmver', async () => {
  it('converts patch "0" to "1"', () => {
    const v = version("1.2.0", "456", true);
    assert.strictEqual(v, "1.2.1099000000000456")
  });

  it('converts patch "9" to "10"', () => {
    const v = version("1.2.9", "456", true);
    assert.strictEqual(v, "1.2.1099000000000456")
  });

  it('rejects patch > "89"', () => {
    let err = null;
    try {
      const v = version("1.2.90", "456", true);
    } catch (e) {
      err = e;
    }
    assert.match(err.message, /patch number cannot exceed 89/);
  });

  it('rejects non-integer JOB_ID', () => {
    let err = null;
    try {
      const v = version("1.2.1", "crunchy raw unboned real dead frog", true);
    } catch (e) {
      err = e;
    }
    assert.match(err.message, /JOB_ID is not an integer/);
  });

  describe('absorbs varying magnitude JOB_ID', () => {
    it('absorbs 1 place', () => {
      const v = version("1.2.3", "6", true);
      assert.strictEqual(v, "1.2.3099000000000006")
    });

    it('absorbs 2 places', () => {
      const v = version("1.2.3", "67", true);
      assert.strictEqual(v, "1.2.3099000000000067")
    });

    it('absorbs 3 places', () => {
      const v = version("1.2.3", "678", true);
      assert.strictEqual(v, "1.2.3099000000000678")
    });

    it('... absorbs 12 places', () => {
      const v = version("1.2.3", "123456789012", true);
      assert.strictEqual(v, "1.2.3099123456789012")
    });
  });

  describe('with new_ci', () => {
    it('with new_ci, generates 16-char patches', () => {
      const v = version("1.2.3", "456", true);
      assert.strictEqual(v, "1.2.3099000000000456")
    });

    it('rejects JOB_ID > 999_999_999_999', () => {
      let err = null;
      try {
        const v = version("1.2.3", "9999999999991", true);
      } catch (e) {
        err = e;
      }
      assert.match(err.message, /JOB_ID cannot exceed 999_999_999_999/);
    });
  });

  describe('without new_ci', () => {
    it('generates 14-char patches', () => {
      const v = version("1.2.3", "456");
      assert.strictEqual(v, "1.2.3090000000456")
    });

    it('rejects JOB_ID > 9_999_999_999', () => {
      let err = null;
      try {
        const v = version("1.2.3", "99999999991");
      } catch (e) {
        err = e;
      }
      assert.match(err.message, /JOB_ID cannot exceed 9_999_999_999/);
    });
  });
});
