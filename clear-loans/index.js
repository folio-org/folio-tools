import { OkapiRequest } from '../okapi-request/index.js';
import DAO from './DAO.js';


/**
 * 1. check in all outstanding loans (this will clear patron blocks due to
 *    items aged to lost; it will also generate lots of fee/fines records)
 * 2. transfer all outstanding fee/fine records (this will close all open fee/fines)
 * 3. cancel all Page requests with request status "Open - Not yet filled"
 * 4. anonymize all closed loans
 * 5. delete all closed fee/fines
 *
 */
class ClearLoans
{
  /**
   * retrieve the first service point
   */
  getServicePoint()
  {
    console.log("retrieving service point...");
    return this.dao.getServicePoints().then((res) => {
      if (res.length) {
        return res[0];
      }

      throw "Could not retrieve any service points!";
    });
  }

  /**
   * retrieve single cancellation-reason by name
   */
  getCancellationReason(name)
  {
    console.log("retrieving cancellation reason...");
    return this.dao.getCancellationReasons(name).then((res) => {
      if (res.length && res.length === 1) {
        return res[0];
      }

      throw "Could not retrieve cancellation reasons!";
    });
  }

  /**
   * retrieve open loans, then check them in at the given service point.
   * return the service point.
   */
  checkInLoans(sp)
  {
    console.log("checking in loans...");
    return this.dao.getOpenLoans().then((loans) => {
      if (loans && Array.isArray(loans) && loans.length > 0) {
        console.log(`(found ${loans.length} loans)`);
        return this.okapi.eachPromise(loans, (l) => {
          return this.dao.checkin(l, sp).then((cl) => {
            console.log(`\tchecked in ${cl.item.barcode}`);
          })
          .catch((err) => {
            const resolution = "Found by library";
            return this.dao.checkin(l, sp, resolution).then((cl) => {
              console.log(`\tchecked in ${cl.item.barcode}`);
            })
            .catch((e) => {
              console.error(`\tcould not check in ${l.item.barcode}`);
              if (e.statusCode && e.body) {
                console.error(`(${e.statusCode}): ${e.body}`);
              } else {
                console.error(e);
              }
            });
          });
        });
      }
    })
    .then(() => sp);
  }

  /**
   * retrieve open accounts, then transfer them at thet given service point.
   * return the service point.
   */
  transferAccounts(sp)
  {
    console.log("transfer outstanding fees/fines");
    return this.dao.getAccounts("Open").then((accounts) => {
      if (accounts && Array.isArray(accounts) && accounts.length > 0) {
        console.log(`(found ${accounts.length} fees/fines)`);
        return this.okapi.eachPromise(accounts, (account) => {
          return this.dao.transferAccount(account, sp).then((ta) => {
            console.log(`\ttransfered $${ta.amount} for ${ta.accountId}`);
          })
          .catch((e) => {
            if (e.statusCode && e.body) {
              console.error(`(${e.statusCode}): ${e.body}`);
            } else {
              console.error(e);
            }
          });
        });
      }
    })
    .then(() => sp);
  }

  /**
   * Cancel open page requests. Return the service point.
   */
  cancelOpenPageRequests(sp)
  {
    console.log('cancel "Open - not yet filled" page requests');
    return this.getCancellationReason("Other").then((reason) => {
      return this.dao.getRequests("Page", "Open - Not yet filled").then((requests) => {
        if (requests && Array.isArray(requests) && requests.length > 0) {
          console.log(`(found ${requests.length} open unfilled Page requests)`);
          return this.okapi.eachPromise(requests, (r) => {
            return this.dao.cancelRequest(r, sp, reason).then((cr) => {
              console.log(`\tcancelled request for ${r.item.barcode}`);
            })
            .catch((e) => {
              if (e.statusCode && e.body) {
                console.error(`(${e.statusCode}): ${e.body}`);
              } else {
                console.error(e);
              }
            });
          });
        }
      })
      .then(() => sp);
    });
  }

  /**
   * Cancel open requests. Return the service point.
   */
  cancelOpenRequests(sp)
  {
    console.log('cancel remaining open requests requests');
    const requestTypes = ['Hold', 'Recall', 'Page'].join(' or ');
    const requestStatuses = ['"Open - Awaiting delivery"', '"Open - Awaiting pickup"', '"Open - In transit"', '"Open - Not yet filled"'].join(' or ');

    return this.getCancellationReason("Patron Cancelled").then((reason) => {
      return this.dao
        .getRequests(requestTypes, requestStatuses)
        .then((requests) => {
          if (requests && Array.isArray(requests) && requests.length > 0) {
            console.log(`(found ${requests.length} open requests)`);
            return this.okapi.eachPromise(requests, (r) => {
              return this.dao.cancelRequest(r, sp, reason)
              .then((cr) => {
                console.log(`\tcancelled request for ${r.item.barcode}`);
              })
              .catch((e) => {
                if (e.statusCode && e.body) {
                  console.error(`(${e.statusCode}): ${e.body}`);
                } else {
                  console.error(e);
                }
              });
            });
          }
        })
        .then(() => sp);
    });
  }

  /**
   * anonymize closed loans
   */
  anonymizeClosedLoans()
  {
    console.log("anonymize closed loans");
    return this.dao.getNonAnonymizedClosedLoans().then((loans) => {
      if (loans && Array.isArray(loans) && loans.length > 0) {
        console.log(`(found ${loans.length} loans)`);
        const userIds = Array.from(new Set(loans.map((l) => l.userId)));
        return this.okapi.eachPromise(userIds, (id) => {
          return this.dao.anonymizeLoans(id).then(() => {
            console.log(`\tanonymized loans for ${id}`);
          });
        });
      }
    });
  }

  /**
   * remove closed accounts
   */
  removeClosedAccounts()
  {
    console.log("delete closed fees/fines");
    return this.dao.getAccounts("Closed").then((accounts) => {
      if (accounts && Array.isArray(accounts) && accounts.length > 0) {
        console.log(`(found ${accounts.length} closed fees/fines)`);
        return this.okapi.eachPromise(accounts, (account) => {
          return this.dao.removeAccount(account).then(() => {
            console.log(`\tremoved ${account.id}`);
          })
          .catch((e) => {
            if (e.statusCode && e.body) {
              console.log(`could not remove ${account.id}; (${e.statusCode}): ${e.body}`);
              console.error(`(${e.statusCode}): ${e.body}`);
            } else {
              console.error(e);
            }
          });
        });
      }
    });
  }

  main()
  {
    try {
      this.okapi = new OkapiRequest(process.argv);
      this.dao = new DAO(this.okapi);

      this.okapi
        .login()
        .then(() => this.getServicePoint())
        .then((sp) => this.checkInLoans(sp))
        .then((sp) => this.transferAccounts(sp))
        .then((sp) => this.cancelOpenPageRequests(sp))
        .then((sp) => this.cancelOpenRequests(sp))
        .then(() => this.anonymizeClosedLoans())
        .then(() => this.removeClosedAccounts())
        .then(() => {
          console.log("Done!");
        })
        .catch((e) => {
          if (e.statusCode && e.body) {
            console.error(`(${e.statusCode}): ${e.body}`);
          } else {
            console.error(e);
          }
        });
    } catch (e) {
      console.error("Unhandled exception:", e);
    }
  }
}

(new ClearLoans()).main();
