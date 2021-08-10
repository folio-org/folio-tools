import https from 'https';
import http from 'http';

/**
 * OkapiRequest
 * A dependency-less Okapi request library for use in node-based scripts.
 *
 * The constructor expects an array of key-value pairs of arguments
 * containing, at least the following:
 *     --username [username]
 *     --password [password]
 *     --tenant [tenant]
 * and either
 *     --okapi [fully-qualified hostname]
 * or
 *     --hostname [hostname]
 *     --port [port]
 * and optionally
 *     --pageSize [item-count to retrieve in a single page]
 *     --streams [page-count to retrieve in parallel]
 *
 *
 * Use it like this:
 *     const okapi = new OkapiRequest(process.argv);
 *     okapi.login()
 *     .then(() => okapi.get('/some/endpoint'))
 *     .then((result) => ...)
 *     .catch(...);
 *
 */
class OkapiRequest
{
  /** information about the authenticated user; populated by this.login() */
  userInfo = null;

  // request-related details, e.g. hostname, headers, etc
  // internal use only:
  requestOptions = {
    "options": {
      "method": "POST",
      "hostname": "",
      "path": "",
      "headers": {
        "Content-type": "application/json",
        "cache-control": "no-cache",
        "accept": "application/json, text/plain"
      },
    },
    "handler": undefined,
  };


  /**
   * request
   * send a request to Okapi; return a Promise containing the response
   *
   * @arg path string, e.g. /foo/bar/bat
   * @arg body object, to be stringified in JSON.stringify(body)
   * @arg method string, one of GET, POST, PUT, DELETE
   */
  request(path, body, method)
  {
    return new Promise((resolve, reject) => {
      const thePath = 0 === path.indexOf('/') ? path : `/${path}`;
      const opts = Object.assign({}, this.requestOptions.options, { path: encodeURI(thePath), method });
      let req = this.requestOptions.handler.request(opts, (res) => {
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
            resolve(res);
          } else {
            reject(res);
          }
        });
      })
      .on('error', function(e) {
        reject(e);
      });

      try {
        if (body) {
          req.write(JSON.stringify(body));
        }
        req.end();
      }
      catch(e) {
         reject(e);
      }
    });
  }


  /**
   * processArgs
   * parse the CLI; throw if a required arg is missing
   *
   * "Usage: node " + __filename + " --username <u> --password <p> --tenant <t> --hostname <h> [--port <p>]"
   * "Usage: node " + __filename + " --username <u> --password <p> --tenant <t> --okapi <o>"
   * "An Okapi URL will parse to values for --hostname and --port."
   *
   * @arg [] args CLI arguments
   * @return {} object shaped like { username, password, okapi, tenant, pesets }
   */
  processArgs(args)
  {
    /**
     * handleHostname
     * set options.hostname; assume https.
     * @arg string a hostname such as example.com
     */
    const handleHostname = (i, config) => {
      config.hostname = i;

      this.requestOptions.handler = https;
      this.requestOptions.options.hostname = i;
    };

    /**
     * handlePort
     * set options.port; assume https for 443, http otherwise.
     * @arg string a string interpretable as a base-10 integer
     */
    const handlePort = (i, config) => {
      const v = Number.parseInt(i, 10);
      if (! isNaN(v)) {
        this.requestOptions.options.port = v;
        this.requestOptions.handler = (i === "443") ? https : http;
      } else {
        throw `The port "${i}" is not a valid number.`;
      }
    };

    /**
     * handleOkapi
     * set options.hostname and optionally options.port. Configure the request
     * handler based on the URL prefix (http or https), but note this will be
     * overriden by the port handler if a port is present.
     * @arg string a URL, e.g. https://www.example.edu
     */
    const handleOkapi = (i, config) => {
      this.requestOptions.handler = (0 === i.indexOf('https')) ? https : http;

      const matches = i.match(/^http[s]?:\/\/([^:/]+):?([0-9]+)?/);
      if (matches && matches.length >= 2) {
        config.hostname = matches[1];
        this.requestOptions.options.hostname = matches[1];
        if (matches[2]) {
          handlePort(matches[2], config);
        }
      } else {
        throw `"${i}" does not look like a URL. Did you forget the http... prefix?`;
      }
    };

    /**
     * handleTenant
     * set options.headers[x-okapi-tenant]
     * @arg string
     */
    const handleTenant = (i, config) => {
      config.tenant = i;
      this.requestOptions.options.headers["x-okapi-tenant"] = i;
    };

    /**
     * handlePageSize; basically atoi
     */
    const handlePageSize = (i, config) => {
      const v = Number.parseInt(i, 10);
      if (! isNaN(v)) {
        config.pageSize = v;
      } else {
        throw `The pageSize value "${i}" is not a valid number.`;
      }
    };

    /**
     * handleStreams; basically atoi
     */
    const handleStreams = (i, config) => {
      const v = Number.parseInt(i, 10);
      if (! isNaN(v)) {
        config.streams = v;
      } else {
        throw `The streams value "${i}" is not a valid number.`;
      }
    };

    // I don't really want the hostname and tenant in here any more now that
    // argument parsing has handler functions, but it's not worth refactoring.
    const config = {
      username: null,
      password: null,
      hostname: null,
      tenant: null,
    };

    // argument handlers
    const handlers = {
      username: (i, config) => { config.username = i; },
      password: (i, config) => { config.password = i; },
      tenant:   handleTenant,
      hostname: handleHostname,
      port:     handlePort,
      okapi:    handleOkapi,
      streams:  handleStreams,
      pageSize: handlePageSize,
    };

    // start at 2 because we get called like "node script.js --foo bar --bat baz"
    // search for pairs of the form
    //   --key value
    // when a key matches a config-key, call its handlers function
    for (let i = 2; i < args.length; i++) {
      let key;
      if (args[i].indexOf('--') === 0) {
        key = args[i].substr(2);
        if (key in handlers && i + 1 < args.length) {
          handlers[key](args[++i], config);
        }
      }
    }

    // make sure all config values are non-empty
    if (Object.values(config).filter(v => v).length == Object.keys(config).length) {
      return config;
    }

    throw `A required argument was not present; missing one of: ${Object.keys(config).join(', ')}.`;
  };


  /**
   *
   */
  constructor(argv)
  {
    // process CLI args; throws if we weren't called correctly
    const config = this.processArgs(argv);

    // login and cache the token
    this.loginCreds = {
      username: config.username,
      password: config.password,
    };

    // how many records to retrieve at once
    this.pageSize = config.pageSize;

    // given an array of promises, how many streams to execute in parallel
    this.streams = config.streams;
  }

  /** get request; return a promise */
  get(path)
  {
    return this.request(path, null, 'GET');
  }

  /**
   * retrieve all entries from a given endpoint in $limit-sized batches;
   * return a promise containing all results in a single array.
   */
  getAll(path, name, batchSize)
  {
    const pageSize = this.pageSize ?? batchSize;
    if (pageSize === 0) {
      throw "You must specify a page-size";
    }

    return this.get(`${path}&limit=0`).then(res => {
      const queries = [];
      const max = res.json.totalRecords;
      console.log(`found ${max} ${name} records`)
      for (let i = 0; i < max; i+= pageSize) {
        queries.push(`${path}&limit=${pageSize}&offset=${i}`);
      }
      let entries = [];
      // console.log(`that'll be ${queries.length} batches of ${pageSize}`)
      let batch = 0;
      return this.eachPromise(queries, (r) => {
        return this.get(r).then(res => {
          // console.log(`retrieved batch ${++batch}`)
          entries = [...entries, ...res.json[name]];
          return entries;
        });
      });
    });
  }

  /** post request; return a promise */
  post(path, body)
  {
    return this.request(path, body, 'POST');
  }

  /** put request; return a promise */
  put(path, body)
  {
    return this.request(path, body, 'PUT');
  }

  /** delete request; return a promise */
  delete(path)
  {
    return this.request(path, null, 'DELETE');
  }

  /**
   * eachPromiseSeries
   * Split an array of Promises into N chunks to be handled in parallel,
   * the items in each chunk being handled in series. e.g given 100 elements
   * and a chunk-size of 4, create 4 parallel streams that handle 25 promises
   * in series, applying the given async function to each.
   * @arg [] arr array of elements
   * @arg function fn function to apply to each element
   * @return promise
   */
  eachPromiseSeries(arr, fn) {
    // console.log('SERIES')
    return arr.reduce((prev, cur) => (prev.then(() => fn(cur))), Promise.resolve());
  }

  /**
   * eachPromiseParallel
   * Split an array of Promises into N partitions to be handled in parallel,
   * the items in each partition being handled in series. e.g given 100 elements
   * and a partition-size of 4, create 4 parallel streams that handle 25 promises
   * in series, applying the given async function to each.
   *
   * @arg [] arr array of elements
   * @arg function fn function to apply to each element
   * @arg int size number of partitions to handle in parallel
   * @return promise
   */
  eachPromiseParallel(arr, fn, partitionSize) {
    // console.log('PARALLEL')
    const size = Math.ceil(arr.length / partitionSize);
    const streams = [];
    for (let i = 0; i < arr.length; i += size) {
      streams.push(this.eachPromiseSeries(arr.slice(i, i + size), fn));
    }

    return Promise.all(streams).then(values => {
      return [].concat(...values);
    });
  };

  /**
   * eachPromise
   * iterate through an array of items IN SERIES, applying the given async
   * function to each element. If this.streams is non-zero, partition the
   * array into streams and handling the streams in parallel but each stream
   * in series.
   *
   * @arg [] arr array of elements
   * @arg function fn function to apply to each element
   * @return promise
   */
  eachPromise(arr, fn)
  {
    if (!Array.isArray(arr)) return Promise.reject(new Error('Array not found'));

    return this.streams ? this.eachPromiseParallel(arr, fn, this.streams) : this.eachPromiseSeries(arr, fn);
  };

  /**
   * login
   * send a post request to bl-users/login with the --username and --password
   * values provided to the constructor. pull the x-okapi-token out of the
   * response header and store it in this.requestOptions; store the response-body
   * in this.userInfo.
   *
   * return a promise
   */
  login()
  {
     return this.post('/bl-users/login', this.loginCreds).then(res => {
       this.requestOptions.options.headers['x-okapi-token'] = res.headers['x-okapi-token'];
       this.userInfo = res.json;
     });
  }
};

export default OkapiRequest;
