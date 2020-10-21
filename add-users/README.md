## create users with permissions read from local files

### usage
```
node $0 --username <u> --password <p> --tenant <t> --hostname <h> --psets <p>
node $0 --username <u> --password <p> --tenant <t> --okapi <http...> --psets <p>
```
where username, password, and tenant are credentials for signing into
the okapi instance available at hostname. Given a hostname via `--hostname`,
handle all requests over https. Given a URL via `--okapi`, parse the value
and determine whether to handle requests with http or https based on the
protocol. psets specifies the path to a directory containing `.json` files,
each containing an array of permission names to add to a permission-set.

### details
given a directory containing a list of json files containing a single
array of strings representing permission set display names, iterate
through the files, for each:

* create a user named for the pset
  * create a corresponding permissions user
  * set the password to match the username
  * assign all service points to the user
* create a pset named for the pset
  * add its permissions to the pset
  * assign its permissions to the user

This script is idempotent; you can run it multiple times. If a user
already exists, its password and permissions will be overwritten.
If a pset already exists, the permissions it contains will be augmented.
