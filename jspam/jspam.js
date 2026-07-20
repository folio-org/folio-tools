import { exec } from 'node:child_process';
import fs from 'node:fs';
import yargs from 'yargs/yargs';
import { hideBin } from 'yargs/helpers';

/**
 * Create tickets for all jira projects associated with packages in
 * the given package.json file. Link them to an existing ticket.
 */
class JSpam {
  /**
   * retrieve an attribute from the MacOS security service
   */
  async getAttr(name, field) {
    return new Promise((res, rej) => {
      exec(String.raw`security find-generic-password -s "${name}" | grep "${field}" | cut -d\" -f 4`, (error, stdout, stderr) => {
        if (error) {
          rej(error);
        }
        res(stdout);
      });
    });
  }


  /**
   * retrieve a password from the MacOS security service
   */
  async getPassword(name, field) {
    return new Promise((res, rej) => {
      exec(`security find-generic-password -s "${name}" -a "${field}" -w`, (error, stdout, stderr) => {
        if (error) {
          rej(error);
        }
        res(stdout);
      });
    });
  }


  async getSecurityServiceCredentials() {
    const username = (await this.getAttr('jira-apitoken', 'acct')).trim();
    const password = (await this.getPassword('jira-apitoken', username)).trim();

    return { username, password }
  }


  /**
   * getCredentials
   * get creds from CLI, or security service
   */
  async getCredentials(argv) {
    if (argv.username && argv.password) {
      return {
        username: argv.username,
        password: argv.password,
      };
    }
    else if (argv.username && argv.token) {
      return {
        username: argv.username,
        password: argv.token,
      };
    }
    else {
      try {
        const creds = await this.getSecurityServiceCredentials();
        return creds;
      } catch (err) {
        throw new Error('could not find credentials', { cause: err });
      }
    }
  }

  jiraHeaders() {
    return {
      'Authorization': `Basic ${Buffer.from(this.credentials.username + ':' + this.credentials.password).toString('base64')}`,
      'Accept': 'application/json',
      'Content-Type': 'application/json'
    };
  }

  /**
   * getMatrix
   * retrieve and parse the team-project responsibility matrix from the given file.
   * transpose it to an object keyed by the project's github name.
   * @param {string} file
   */
  async getMatrix(file) {
    const modules = {};
    const matrix = fs.readFileSync(file, { encoding: 'UTF-8' });

    const teams = matrix.split("\n");

    let pteam = { team: '', po: '', tl: '', github: '', jira: '' };
    teams.forEach((line, count) => {
      const tds = line.split("\t").map((i) => i.replaceAll('"', ''));

      const team = { team: '', po: '', tl: '', github: '', jira: '' };
      tds.forEach((str, j) => {
        let td = str;
        let userId = null;
        if (td.startsWith('=HYPERLINK')) {
          // grab user-id, if available, then sanitize to a simple string
          if (new RegExp(/.*\/wiki\/people\/[a-z0-9]+\?.*/).test(td)) {
            userId = td.replace(/.*\/wiki\/people\/([a-z0-9]+)\?.*/, '$1');
          }
          td = td.replace(/=HYPERLINK\((.*)\)/, '$1').split(';')[1];
        }

        if (j == 0) team.jira = td?.trim();
        if (j == 1) team.team = (td.trim() || pteam.team.trim()).split(/\n/)[0].trim();
        if (j == 2) team.po = td.trim() || pteam.po;
        if (j == 2) team.poid = userId;
        if (j == 3) team.tl = td.trim() || pteam.tl;
        if (j == 3) team.tlid = userId;
        if (j == 5) team.github = td?.trim();
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

  /**
   * timeout
   * Resolve after 200ms to avoid Atlassian rate limiting
   * https://developer.atlassian.com/cloud/jira/platform/rate-limiting/
   *
   * @return Promise
   */
  timeout() {
    return new Promise(res => {
      setTimeout(() => res(), 200);
    });
  }

  /**
   * teamForName
   * provide a map from team-name (in the team-project responsibility matrix)
   * to its ID in Jira.
   *
   * astonishingly, custom-field value-lists are not accessible via the API
   * without admin-level access. I don't get it.
   * @param {*} name
   */
  async teamForName(name) {
    const teams = {
      "@cult": 10138,
      "Aggies": 10139,
      "Bama": 10140,
      "Bienenvolk": 10141,
      "Bienenvolk (fka ERM)": 10141,
      "Bienenvolk (fka ERM Delivery)": 10141,
      "ERM Subgroup Dev Team": 10141,
      "ERM Delivery": 10141,
      "Citation": 10142,
      "Core: Platform": 10144,
      "Core Platform": 10144,
      "Corsair": 10145,
      "EBSCO - FSE": 10147,
      "Eureka": 10149,
      "Dreamliner": 10150,
      "Firebird": 10152,
      "Firebird team": 10152,
      "Folijet": 10153,
      "Folijet team": 10153,
      "FOLIO DevOps": 10155,
      "Frontside": 10156,
      "Gutenberg": 10158,
      "K-Int": 10159,
      "Kinetics": 10160,
      "Kitfox": 10161,
      "Lehigh": 10162,
      "NSIP(Lehigh)": 10162,
      "Leipzig": 10163,
      "Mjolnir": 10164,
      "MOL": 10165,
      "Mriya": 10166,
      "NLA": 10167,
      "Odin": 10169,
      "Other dev": 10170,
      "PTF": 10172,
      "Qulto": 10173,
      "Reporting": 10174,
      "Reservoir Dogs": 10175,
      "Scanbit": 10176,
      "Scout": 10177,
      "Sif": 10178,
      "Siphon": 10179,
      "Spitfire": 10180,
      "Spitfire Team": 10180,
      "Spring Force": 10181,
      "Stacks": 10182,
      "Stripes Force": 10183,
      "Thor": 10184,
      "Thunderjet": 10185,
      "Thunderjet Team": 10185,
      "UNAM": 10186,
      "Vega": 10187,
      "Vega Team": 10187,
      "Volaris": 10188,
      "仁者无敌 \"Benevolence\"": 10189,
      "Nighthawk": 10495,
      "ASA": "",
      "Klemming": "",
      "Dojo": ""
    };

    // even if we _don't_ have a project for the given name, we still
    // resolve, not reject, because we still want to create the ticket;
    // it just won't be assignable to a team.
    await this.timeout();
    if (teams[name]) {
      const team = await (await fetch(`${this.jira}/rest/api/3/customFieldOption/${teams[name]}`)).json();
      team.id = `${teams[name]}`;

      return team;
    }
    else {
      console.warn(`Could not match team "${name}"`);
      return null;
    }
  }


  async createTicket({ summary, description, project, parent, labels, team, cc, assignee }) {
    const body = {
      "fields": {
        "project": { id: project.id },
        summary,
        issuetype: { id: this.taskType.id },
        description: {
          "content": [
            {
              "content": [
                {
                  "text": description,
                  "type": "text"
                }
              ],
              "type": "paragraph"
            }
          ],
          "type": "doc",
          "version": 1
        }
      }
    };

    if (parent) {
      body.fields.parent = { key: parent };
    }

    body.fields.labels = Array.isArray(labels) ? labels : labels?.split(',');

    if (team) {
      body.fields.customfield_10057 = team;
    }

    if (cc?.length) {
      cc.forEach((i) => {
        body.fields.description.content[0].content.push(
          {
            "text": "\nCC: ",
            "type": "text"
          },
          {
            "type": "mention",
            "attrs": {
              "id": i.id,
              "text": i.name,
            }
          }
        );
      });
    }

    if (assignee) {
      body.fields.assignee = assignee;
    }

    return fetch(`${this.jira}/rest/api/3/issue`, {
      headers: this.jiraHeaders(),
      body: JSON.stringify(body),
      method: 'POST',
    }).then(res => res.json());
  }


  linkTicket(inward, outward) {
    const body = {
      "outwardIssue": {
        "key": outward.key,
      },
      "inwardIssue": {
        "key": inward.key,
      },
      "type": this.relatesLink,
    };
    return fetch(`${this.jira}/rest/api/3/issueLink`, {
      headers: this.jiraHeaders(),
      body: JSON.stringify(body),
      method: 'POST',
    });
  }


  parseArgv() {
    return yargs(hideBin(process.argv))
      .usage('Usage: $0 --summary <s> --description <d> --link <JIRA-123> --package <package.json>')

      .option('s', {
        alias: 'summary',
        describe: 'issue summary (title)',
        type: 'string',
      })

      .option('d', {
        alias: 'description',
        describe: 'issue description',
        type: 'string',
      })

      .option('p', {
        alias: 'package',
        describe: 'path to a package.json file to parse',
        type: 'string',
      })

      .option('l', {
        alias: 'link',
        describe: 'jira issue[s] to link to',
        type: 'string',
      })

      .option('e', {
        alias: ['parent', 'epic'],
        describe: 'jira parent issue (formerly epic)',
        type: 'string',
      })

      .option('label', {
        describe: 'jira label[s] to apply',
        type: 'string',
      })

      .option('team', {
        describe: 'assign tickets to teams per team-module-responsibility matrix',
        type: 'boolean',
      })

      .option('ccpo', {
        describe: 'CC the product owner per team-module-responsibility matrix in the ticket description',
        type: 'boolean',
      })

      .option('cctl', {
        describe: 'CC the tech lead per team-module-responsibility matrix in the ticket description',
        type: 'boolean',
      })

      .option('username', {
        describe: 'jira username',
        type: 'string',
      })

      .option('token', {
        describe: 'jira API token',
        type: 'string',
      })

      .demandOption(['s', 'd', 'package'])
      .help('h')
      .alias('h', 'help')
      .argv;
  }


  /**
   * eachPromise
   * iterate through an array of items IN SERIES, applying the given async
   * function to each, with a delay between each element.
   * @arg [] arr array of elements
   * @arg function fn function to apply to each element
   * @return promise
   */
  eachPromise(arr, fn) {
    //
    if (!Array.isArray(arr)) return Promise.reject(new Error('Array not found'));
    return arr.reduce((prev, cur) => {
      return prev
        .then(this.timeout)
        .then(() => fn(cur))
    }, Promise.resolve());
  };


  async main() {
    this.jira = 'https://folio-org.atlassian.net';

    // const contents = JSON.parse(fs.readFileSync(filename, { encoding: 'UTF-8'}));
    //
    // jspam --username --token
    //    --link SOME-JIRA -l OTHER-JIRA
    //    --summary "some title"
    //    --description "some description"
    //    --package ./path/to/some/package.json
    try {
      this.argv = this.parseArgv();

      this.credentials = await this.getCredentials(this.argv);

      this.types = await (await fetch(`${this.jira}/rest/api/3/issuetype`)).json();
      // what the ...? I SWEAR TO GOD I don't understand what is happening
      // here, but when I make this request with Axios, name has english values.
      // when I make it with fetch, name is Chinese:
      // [
      //   'Query',     '改进',
      //   '任务',      'Scenario',
      //   'Prototype', '新增功能',
      //   '缺陷',      '子任务',
      //   'Template',  '长篇故事',
      //   'Umbrella',  'Tech Debt',
      //   '故事'
      // ]
      // [
      //   'Query',     'Improvement',
      //   'Task',      'Scenario',
      //   'Prototype', 'New Feature',
      //   'Bug',       'Sub-task',
      //   'Template',  'Epic',
      //   'Umbrella',  'Tech Debt',
      //   'Story'
      // ]
      this.taskType = this.types.find(type => type.untranslatedName === 'Task');

      this.linkTypes = await (await fetch(`${this.jira}/rest/api/3/issueLinkType`)).json();
      this.relatesLink = this.linkTypes.issueLinkTypes.find(link => link.name === 'Relates');

      // the live data now comes in via an iframe with a fancy export-to-csv function
      // that, regrettably, does not have a stable URL :( instead, the export is saved
      // here as matrix.csv and loaded locally
      const matrix = await this.getMatrix('./matrix.csv');

      // get ticket from Jira
      let link;
      if (this.argv.link) {
        link = await (await fetch(`${this.jira}/rest/api/3/issue/${this.argv.link}`)).json();
      }

      // map dependencies:
      // @folio/stripes-lib => stripes-lib
      // @folio/some-app => ui-some-app
      // @okapi/some-app => some-app
      const contents = JSON.parse(fs.readFileSync(this.argv.package, { encoding: 'UTF-8' }));
      const deps = Object.keys(contents.dependencies)
        .map(p => {
          if (p.startsWith('@folio/stripes-')) {
            return p.substring(p.indexOf('/') + 1);
          }
          if (p.startsWith('@folio')) {
            return `ui-${p.substring(p.indexOf('/') + 1)}`;
          }
          if (p.startsWith('@okapi')) {
            return p.substring(p.indexOf('/') + 1);
          }
        })
        .filter(Boolean)
        .sort((a, b) => a.localeCompare(b));

      // get projects from JIRA
      // generally, name corresponds to GitHub repository name, and thus can be used
      // to map between the matrix and Jira
      (await fetch(`${this.jira}/rest/api/3/project`)).json()
        .then(projects => {
          // map the array of projects into a hash keyed by name, e.g. ui-some-app
          const pmap = {};
          projects.forEach(p => { pmap[p.name] = p; });

          // fill in holes in Jira's map with values from the matrix if possible.
          // this happens when the Jira name does not correspond to a repo name
          // but the matrix provides such a mapping, e.g. for all the ERM projects
          // that are in separate repos but share a common Jira project.
          Object.keys(matrix).forEach(k => {
            if (!pmap[k]) {
              const match = Object.values(pmap).find(jira => jira.key === matrix[k].jira);
              if (match) {
                // console.log(`+ ${k} ${match.key} ${match.name}`)
                pmap[k] = match;
              }
            }
          });

          this.eachPromise(deps, d => {
            if (pmap[d] && matrix[d]) {
              this.teamForName(matrix[d].team)
                .then(team => {
                  // only assign the team if we received --team
                  const t = this.argv.team ? team : null;
                  const cc = [];
                  if (this.argv.ccpo && matrix[d].poid) {
                    cc.push({ id: matrix[d].poid, name: matrix[d].po })
                  }

                  if (this.argv.cctl && matrix[d].tlid) {
                    cc.push({ id: matrix[d].tlid, name: matrix[d].tl })
                  }

                  return this.createTicket({
                    summary: this.argv.summary,
                    description: this.argv.description,
                    project: pmap[d],
                    parent: this.argv.parent,
                    labels: this.argv.label,
                    team: t,
                    cc: cc,
                  })
                })
                .then(ticket => {
                  if (link) {
                    this.linkTicket(ticket, link);
                  }
                  return ticket;
                })
                .then(async (ticket) => {
                  console.log(`created ${ticket.key} (${d})`)
                })
                .catch(e => {
                  console.error(e);
                });
            }
            else {
              console.warn(`could not find a jira project or matrix entry matching >>${d}<<`);
            }
          });
        })
    }
    catch (e) {
      console.error(e);
    };
  }
}

(new JSpam()).main();
