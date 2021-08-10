## A dependency-less Okapi request library for use in node-based scripts

### OkapiRequest

The `OkapiRequest` class provides the following functions that return Promises:

* `login()`
* `get(path)`
* `getAll(path, object-name, page-size)`
* `post(path, {})`
* `put(path, {})`
* `delete(path)`

The constructor takes an array and should be called like
```
const o = new OkapiRequest(['--username', 'some-u', '--password', 'some-pw', ...])
```
Where the `--` keys include the following: `username`, `password`, `tenant`,
and either (`hostname` and `port`) or (`okapi`). Optional keys are `pageSize`
and `streams`.

If `process.argv` contains `--pageSize N`, it will override the given page-size.

If `process.argv` contains `--streams N`, `getAll` will execute N queries in
parallel. Without `--streams`, `getAll` always executes in series. e.g. if
there are 100 rows, `--pageSize 25` will execute 4 queries in series whereas
`--pageSize 25 --streams 4` will execute 2 parallel streams, each with 2
queries running in series.

### usage

```
const okapi = new OkapiRequest(process.argv);
okapi.login()
  .then(() => okapi.get('/some/endpoint'))
  .then((result) => ...)
  .catch(...);
```
