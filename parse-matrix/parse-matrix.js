const axios = require("axios");
const { parse } = require('node-html-parser');

/**
 * Create tickets for all jira projects associated with packages in
 * the given package.json file. Link them to an existing ticket.
 */
class ParseMatrix {
  /**
   * getMatrix
   * retrieve and parse the team-project responsibility matrix from the given URL.
   * transpose it to an object keyed by the project's github name.
   * @param {*} matrixUrl
   */
  async getMatrix(matrixUrl)
  {
    const modules = {};
    const matrix = (await axios.get(matrixUrl)).data;

    const userFromTd = (td) => {
      return td.querySelector ? td.querySelector('a')?.getAttribute('data-username') : null;
    }

    const teams = parse(matrix).querySelectorAll('.confluenceTable tbody tr');

    // pluck the first row, pretending it's a <thead> effectively,
    // so it can be used as a template for parsing other rows
    // which may have missing team or product-owner cells because
    // a td above spans multiple rows.
    const ths = Array.from(teams.shift().querySelectorAll('td'));

    let pteam = { team: '', po: '', tl: '', github: '', jira: '' };
    teams.forEach((tr, i) => {
      const tds = Array.from(tr.querySelectorAll('td'));

      // jigger tds so it always resembles ths, i.e. so there is always a 1::1
      // correspondence between the th and the td. if we have a table like this:
      //
      // | TEAM | PO | TL | junk | REPO | JIRA |
      // | Aaaa | Aa | Aa | junk | Aaaa | Aaaa |
      // |      | Bb | Bb | junk | Bbbb | Bbbb |
      // | Cccc | Cc | Cc | junk | Cccc | Cccc |
      // |      |    | Dd | junk | Dddd | Dddd |
      //
      // then the A-row and C-row have the same number of cols, but the B-row
      // is short by one and the D-row is short by two because of the cells
      // above that span multiple rows.

      while (tds.length < ths.length) {
        tds.unshift({ text: '' });
      }

      const team = { team: '', po: '', tl: '', github: '', jira: '' };
      // I don't really know what kind of data structure `tds` is.
      // iterating with (td, j) works just fine, but trying to access tds[j] fails.
      tds.forEach((td, j) => {
        if (j == 0) team.team = td.text || pteam.team;
        if (j == 1) team.po = userFromTd(td) || pteam.po;
        if (j == 2) team.tl = userFromTd(td) || pteam.tl;
        if (j == 4) team.github = td.text;
        if (j == 5) team.jira = td.text;
      });

      if (team.github) {
        modules[team.github] = team;
      }

      // cache current team to deal with rowspans, i.e. rows that inherit
      // their first few fields from a parent row.
      pteam = team;
    });

    return modules;
  }

  async main()
  {
    try {
      const matrix = await this.getMatrix('https://wiki.folio.org/display/REL/Team+vs+module+responsibility+matrix');
      console.log(JSON.stringify(matrix, null, 2));
    }
    catch(e) {
      console.error(e);
    };
  }
}

(new ParseMatrix()).main();
