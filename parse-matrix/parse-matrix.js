import axios from 'axios';
import { parse } from 'node-html-parser';

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
    // const matrix = fs.readFileSync('/Users/zburke/Downloads/matrix.html', { encoding: 'UTF-8' });

    const userFromTd = (td) => {
      let name = td.querySelector ? td.querySelector('a')?.getAttribute('data-username')?.trim() : null;
      if (name) {
        name = name.replace(/\s+/g, ' ');
      }
      return name;
    }

    const container = parse(matrix).querySelector('.confluenceTable');
    const rows = Array.from(container.querySelectorAll('tbody tr'));
    rows.forEach((tr, i) => {
      const tds = Array.from(tr.querySelectorAll('td'));
      const team = { team: '', po: '', tl: '', github: '', jira: '' };
      // I don't really know what kind of data structure `tds` is.
      // iterating with (td, j) works just fine, but trying to access tds[j] fails.
      tds.forEach((td, j) => {
        if (j == 0) team.jira = td.text?.trim();
        if (j == 1) team.team = (td.text?.trim()).split(/\n/)[0].trim();
        if (j == 2) team.po = userFromTd(td);
        if (j == 3) team.tl = userFromTd(td);
        // there is no rule 4
        if (j == 5) team.github = td.text?.trim();
      });

      if (team.github) {
        modules[team.github] = team;
      }
    });

    return modules;
  }

  async main()
  {
    try {
      const matrix = await this.getMatrix('https://wiki.folio.org/pages/viewpage.action?pageId=14463134');
      console.log(JSON.stringify(matrix, null, 2));
    }
    catch(e) {
      console.error(e);
    };
  }
}

(new ParseMatrix()).main();
