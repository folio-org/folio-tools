/**
 * data access methods; they return promises
 */
class DAO
{
  /** size of batches to retrieve */
  limit = 100;


  /**
   * retrieve all open loans, in $limit sized-batches; return a single array
   */
  getOpenLoans()
  {
    return this.okapi.getAll('/circulation/loans?query=status.name=="Open" sortby id', 'loans', this.limit);
  }

  /**
   * check in the given loan at the given service point
   */
  checkin(loan, sp, resolution)
  {
    if (loan.item.barcode) {
      const body = {
        itemBarcode: loan.item.barcode,
        servicePointId: sp.id,
        checkInDate: new Date().toISOString(),
      };

      if (resolution) {
        body.claimedReturnedResolution = resolution;
      }

      return this.okapi.post('/circulation/check-in-by-barcode', body).then(res => res.json);
    }

    throw `Could not renew loan ${loan.id}; the item lacked a barcode.`;
  }

  /**
   * retrieve up to 100 service points
   */
  getServicePoints()
  {
    return this.okapi.get('/service-points?limit=100').then(res => {
      return res.json.servicepoints;
    });
  }

  /**
   * retrieve all accounts by status, in $limit sized-batches; return a single array
   */
  getAccounts(status) {
    return this.okapi.getAll(`/accounts?query=status.name=="${status}" sortby id`, 'accounts', this.limit);
  }

  /**
   * transfer the given account from the given service point with the
   * user-name "Automated Process".
   */
  transferAccount(account, sp)
  {
    const body = {
      amount: `${account.remaining}`,
      notifyPatron: false,
      servicePointId: sp.id,
      userName: "Automated Process",
      paymentMethod: "Cash",
    };

    return this.okapi.post(`/accounts/${account.id}/transfer`, body).then(res => res.json);
  }

  /**
   * remove the given account from
   */
  removeAccount(account)
  {
    return this.okapi.delete(`/accounts/${account.id}`);
  }

  /**
   * get cancellation reasons matching name
   */
  getCancellationReasons(name)
  {
    return this.okapi.get(`/cancellation-reason-storage/cancellation-reasons?query=name=="${name}"&limit=100`).then(res => {
      return res.json.cancellationReasons;
    });
  }

  /**
   * get requests given lists of types and statuses, in $limit-sized batches;
   * return a single array.
   *
   * @param {string} types or-separated list of types
   * @param {string} statuses or-separated list of statuses
   *
   */
  getRequests(types, statuses)
  {
    return this.okapi.getAll(`/request-storage/requests?query=requestType==(${types}) ${statuses ? ` and status==(${statuses})` : ''} sortby id`, 'requests', this.limit);
  }

  /**
   * cancel a request (change its status to "Closed - Cancelled") with the
   * given service point and reason. pull the cancelledByUserId value from
   * this.okapi.
   */
  cancelRequest(request, sp, reason)
  {
    const body = {
      ...request,
      cancelledByUserId: this.okapi.userInfo.user.id,
      cancellationReasonId: reason.id,
      cancellationAdditionalInformation: '',
      cancelledDate: new Date().toISOString(),
      status: 'Closed - Cancelled',
    }

    return this.okapi.put(`/circulation/requests/${request.id}`, body).then(res => res.json);
  }

  /**
   * get non-anonymized, closed loans in $limit-sized batches; return a single array.
   */
  getNonAnonymizedClosedLoans()
  {
    return this.okapi.getAll('/circulation/loans?query=status.name==Closed and userId="" sortby id', 'loans', this.limit);
  }

  /**
   * anonymize loans for the given user-id.
   */
  anonymizeLoans(userId)
  {
    return this.okapi.post(`/loan-anonymization/by-user/${userId}`);
  }

  constructor(okapi)
  {
    this.okapi = okapi;
  }
}

export default DAO;
