## purge loan, fee/fine, and request data

### details

1. check in all outstanding loans (this will clear patron blocks due to
   items aged to lost; it will also generate lots of fee/fines records)
2. transfer all outstanding fee/fine records (this will close all open fee/fines)
3. cancel all Page requests with request status "Open - Not yet filled" with reason "Other"
4. cancel all requests with any "open" status with reason "Patron cancelled"
5. anonymize all closed loans
6. delete all closed fee/fines

### usage
```
node $0 --username <u> --password <p> --tenant <t> --hostname <h> --port <p>
node $0 --username <u> --password <p> --tenant <t> --okapi <http...>
```
where username, password, and tenant are credentials for signing into
the okapi instance available at hostname. Given a hostname via `--hostname`,
handle all requests over https. Given a URL via `--okapi`, parse the value
and determine whether to handle requests with http or https based on the
protocol.
