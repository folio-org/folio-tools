## A dependency-less Okapi request library for use in node-based scripts

### OkapiRequest

The `OkapiRequest` class provides the following functions that return Promises:

* `login()`
* `get(path)`
* `getAll(path, object-name, batch-size)`
* `post(path, {})`
* `put(path, {})`
* `delete(path)`

The constructor takes an array and should be called like
```
const o = new OkapiRequest(['--username', 'some-u', '--password', 'some-pw', ...])
```
Where the `--` keys include the following: `username`, `password`, `tenant`,
and either (`hostname` and `port`) or (`okapi`).

### usage

```
const okapi = new OkapiRequest(process.argv);
okapi.login()
  .then(() => okapi.get('/some/endpoint'))
  .then((result) => ...)
  .catch(...);
```
