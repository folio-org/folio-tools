const https = require('https');
const fs = require('fs');
const util = require('util');


/**
 * create users with permissions read from local files
 * usage: node $0 some-url some-directory
 * e.g. node add-users.js folio-snapshot-okapi.dev.folio.org ./psets
 *
 * given a directory containing a list of json files containing a single array
 * of strings representing permission set display names,
 * iterate through the files, for each:
 *   create a user named for the pset
 *     create a corresponding permissions user
 *     set the password to match the username
 *   create a pset named for the pset
 *     add its permissions to the pset
 *     assign its permissions to the user
 *
 * this script is idempotent; you can run it multiple times.
 * if a user already exists, its password and permissions will be
 * overwritten.
 * if a pset already exists, the permissions it contains will be augmented.
 *
 * TODO: if a user already exists, remove existing permissions.
 * TODO: if a pset already exists, remove existing permissions.
 */

/**
 * HTTP request config
 */
const options = {
  "method": "POST",
  "hostname": "",
  "path": "",
  "headers": {
    "Content-type": "application/json",
    "cache-control": "no-cache",
    "accept": "application/json"
  }
};

/**
 * okapiRequest
 * send a request to Okapi; return a Promise containing the response
 *
 * @arg path string, e.g. /foo/bar/bat
 * @arg body object, to be stringified in JSON.stringify(body)
 * @arg method string, one of GET, POST, PUT, DELETE
 * @arg cb function of the shape (err, value) => { ... }, error-first callback
 */
const okapiRequest = util.promisify((path, body, method, cb) => {
  const thePath = 0 === path.indexOf('/') ? path : `/${path}`;
  const opts = Object.assign({}, options, { path: thePath, method });
  let req = https.request(opts, (res) => {
    const chunks = [];
    res.on("data", function (chunk) {
      chunks.push(chunk);
    });

    res.on("end", function () {
      res.body = chunks.join("")
      if (res.statusCode >= 200 && res.statusCode < 300) {
        if (res.body) {
          res.json = JSON.parse(res.body);
        }
        cb(null, res);
      } else {
        // console.error(`ERROR: Status Code: ${res.statusCode}; ${chunks.join('')}`);
        cb(res);
      }
    });
  })
  .on('error', function(e) {
    cb(e);
  });

  try {
    if (body) {
      req.write(JSON.stringify(body));
    }
    req.end();
  }
  catch(e) {
    cb(e);
  }
});

const okapiGet = util.promisify((path, cb) => okapiRequest(path, null, 'GET', cb));
const okapiPost = util.promisify((path, body, cb) => okapiRequest(path, body, 'POST', cb));
const okapiPut = util.promisify((path, body, cb) => okapiRequest(path, body, 'PUT', cb));
const okapiDelete = util.promisify((path, cb) => okapiRequest(path, null, 'DELETE', cb));

/**
 * toUser
 * extract a user object from a response
 * @return object
 */
const toUser = (o) => {
  if (o && o.resultInfo.totalRecords === 1) {
    return o.users[0];
  }
  throw "response was not an object, or did not contain a single user";
};

/**
 * credentialsExist
 * determine if credentials exist for the given user
 * @return boolean
 */
const credentialsExist = async (user) => {
  const res = await okapiGet(`/authn/credentials-existence?userId=${user.id}`);
  return res.json.credentialsExist;
};

/**
 * createUser
 * create a user with the following attributes:
 * username: username
 * barcode: a number
 * active: true
 * type: "patron"
 * patronGroup: id of the 'staff' group
 * personal: { lastName: "Admin", firstName: username}
 *
 * @return object
 */
const createUser = async (username) => {
  const groups = await okapiGet('/groups?query=group==staff');
  if (groups.json.totalRecords === 1) {
    const group = groups.json.usergroups[0];
    const user = {
      username,
      barcode: `${new Date().valueOf()}${Math.floor(Math.random() * Math.floor(999999))}`,
      active: true,
      type: "patron",
      patronGroup: group.id,
      personal: {
        "lastName": "Admin",
        "firstName": username,
      }
    };

    const res = await okapiPost('/users', user);
    return res.json
  } else {
    throw "response was not an object, or did not contain a single patron group";
  }
}

/**
 * getOrCreateUser
 * given a username, retrieve the corresponding user, or create it if it
 * does not exist.
 * @return object
 */
const getOrCreateUser = async (username) => {
  const res = await okapiGet(`/users?query=username==${username}`);
  if (res.json.totalRecords === 1) {
    console.log(`found ${username}`)
    return toUser(res.json);
  } else {
    console.log(`created ${username}`)
    return createUser(username);
  }
}

/**
 * assignPermissionsUser
 * retrieve the permissions user; create one if one does not exist.
 */
const assignPermissionsUser = async (user) => {
  // okapiGet throws if the response is non-200, but we may receive 404s here
  try {
    const res = await okapiGet(`/perms/users/${user.id}/permissions?indexField=userId`);
    console.log(`  found permissions-user ${user.username}`)
  }
  catch(e) {
    console.log(`  created permissions-user ${user.username}`)
    const puser = {
      userId: user.id,
      permissions: [],
    };

    await okapiPost('/perms/users', puser);
  }
}

/**
 * assignCredentials
 * assign credentials for a user, overwriting existing values if they exist.
 * the password will be the username, WHICH IS TOTALLY AWESOME.
 * @arg user object
 */
const assignCredentials = async (user) => {
  if (await credentialsExist(user)) {
    // console.log(`  deleting credentials for ${username}`)
    await okapiDelete(`/authn/credentials?userId=${user.id}`);
  }
  const creds = {
    username: user.username,
    password: user.username,
    userId: user.id,
  };

  // console.log(`  set credentials for ${username}`)
  await okapiPost('/authn/credentials', creds);
}

/**
 * getOrCreatePset
 */
const getOrCreatePset = async (name, filename, permissions) => {
  // read the array of displayNames from the file, then map from displayName
  // to permissionName
  const contents = JSON.parse(fs.readFileSync(filename, { encoding: 'UTF-8'}));
  const subPermissions = [];
  contents.forEach(d => {
    if (permissions[d]) {
      subPermissions.push(permissions[d]);
    } else {
      console.error(`Could not find the permission "${d}".`);
    }
  });

  const pset = {
    "displayName": name,
    "mutable": true,
    subPermissions
  };

  const psets = await okapiGet(`/perms/permissions?query=displayName==${name}`);
  if (psets.json.totalRecords === 1) {
    console.log(`  found pset ${name}`)
    pset.id = psets.json.permissions[0].id;
    pset.permissionName = psets.json.permissions[0].id;
    const res = await okapiPut(`/perms/permissions/${pset.id}`, pset);
    return res.json;
  } else {
    console.log(`  created pset ${name}`)
    const res = await okapiPost('/perms/permissions', pset);
    return res.json;
  }
};

/**
 * assignPermissions
 * assign the permissions in the given pset to the given user, one by one,
 * in series.
 * @arg object user
 * @arg object pset
 */
const assignPermissions = (user, pset) => {
  eachPromise(pset.subPermissions, (p) => {
    const up = {
      permissionName: p,
    };
    console.log(`  granting ${p} to ${user.username}`)
    okapiPost(`/perms/users/${user.id}/permissions?indexField=userId`, up)
    .catch(err => {
      try {
        const e = JSON.parse(err.body)
        console.error(e.errors[0].message)
      }
      catch(e) {
        console.error(e.body);
      }
    });
  });
};

/**
 * configureUser
 * given a username:
 * 1. retrieve or create the user
 * 2. write credentials, overwriting them if they exist
 * 3. create a pset
 * 4. assign it to the user
 *
 * @arg string p, name of a file to read, e.g. some-user.json
 * @arg string path, path to directory containing p, e.g. ./foo/bar
 * @arg object permissions, map from displayName => permissionName
 */
const configureUser = async (p, path, permissions) => {
  try {
    const username = p.match(/(.*)\.json/)[1];

    const user = await getOrCreateUser(username);
    await assignPermissionsUser(user);
    await assignCredentials(user);
    const pset = await getOrCreatePset(username, `${path}/${p}`, permissions);
    await assignPermissions(user, pset);
  }
  catch(e) {
    console.error(e);
  }
};

/**
 * getPermissions
 * retrieve all permissions. Return an object mapping displayName => permissionName
 */
const getPermissions = async () => {
  const res = await okapiGet('/perms/permissions?query=visible==true%20and%20mutable==false&length=2000');
  if (res.json.totalRecords) {
    const hash = {};
    res.json.permissions.forEach(p => {
      hash[p.displayName] = p.permissionName;
    });

    return hash;
  }
  throw "Could not retrieve permissions";
};

/**
 * processArgs
 * parse the CLI; throw if a required arg is missing
 *
 * @arg [] args CLI arguments
 * @return {} object shaped like { username, password, hostname, tenant, pesets }
 */
const processArgs = (args) => {
  const config = {
    username: null,
    password: null,
    hostname: null,
    tenant: null,
    psets: null,
  };

  // start at 2 because we get called like "node script.js --foo bar --bat baz"
  // search for pairs of the form
  //   --key value
  // and populate the config object with them
  for (let i = 2; i < args.length; i++) {
    let key;
    if (args[i].indexOf('--') === 0) {
      key = args[i].substr(2);
      if (key in config && i + 1 < args.length) {
        config[key] = args[i + 1]; // capture the key-value pair ...
        i++;                       // ... and skip to the next potential key
        continue;
      }
    }
  }

  // make sure all config values are non-empty
  if (Object.values(config).filter(v => v).length == Object.keys(config).length) {
    return config;
  }

  console.log("Usage: node " + __filename + " --username <u> --password <p> --tenant <t> --hostname <h> --psets <p>");

  throw `A required argument was not present; missing one of: ${Object.keys(config).join(', ')}.`;
};

/**
 * eachPromise
 * iterate through an array of items IN SERIES, applying the given async
 * function to each.
 * @arg [] arr array of elements
 * @arg function fn function to apply to each element
 * @return void
 */
const eachPromise = (arr, fn) => {
  if (!Array.isArray(arr)) return Promise.reject(new Error('Array not found'));
  return arr.reduce((prev, cur) => (prev.then(() => fn(cur))), Promise.resolve());
};

/**
 * main:
 * login
 * get all visible permissions
 * read pset directory
 * foreach pset
 *   create a corresponding user
 *     create a corresponding permissions-user
 *     set the password
 *   create a corresponding pset
 *     add permissions
 *     assign pset to user
 */
async function main() {
  try {
    // process CLI args; throws if we weren't called correctly
    config = processArgs(process.argv);

    options.hostname = config.hostname;
    options.headers["x-okapi-tenant"] = config.tenant;

    // login and cache the token
    const loginCreds = {
      username: config.username,
      password: config.password,
    };
    const res = await okapiPost('/authn/login', loginCreds)
    options.headers['x-okapi-token'] = res.headers['x-okapi-token'];

    const path = config.psets;

    const permissions = await getPermissions();
    const psets = fs.readdirSync(path);
    if (psets.length) {
      eachPromise(psets, (p) => configureUser(p, path, permissions));
    } else {
      console.error(`Found ${path} but it was empty :(`)
      process.exit(1);
    }
  }
  catch (e) {
    console.error(e.message);
    process.exit(1);
  }
};

main();
