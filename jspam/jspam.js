const { exec } = require("child_process");
const yargs = require('yargs/yargs')
const { hideBin } = require('yargs/helpers')
const axios = require("axios");
const fs = require('fs');
const { parse } = require('node-html-parser');

/**
 * Create tickets for all jira projects associated with packages in
 * the given package.json file. Link them to an existing ticket.
 */
class JSpam {
  /**
   * retrieve an attribute from the MacOS security service
   */
  getAttr(name, field)
  {
    return new Promise((res, rej) => {
      exec(`security find-generic-password -s "${name}" | grep "${field}" | cut -d\\" -f 4`, (error, stdout, stderr) => {
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
  getPassword(name, field)
  {
    return new Promise((res, rej) => {
      exec(`security find-generic-password -s "${name}" -a "${field}" -w`, (error, stdout, stderr) => {
        if (error) {
          rej(error);
        }
        res(stdout);
      });
    });
  }


  getSecurityServiceCredentials()
  {
    const credentials = {  };
    return this.getAttr('jira-password', 'acct')
    .then(username => {
      credentials.username = username.trim();
      return credentials.username;
    })
    .then(username => this.getPassword('jira-password', username))
    .then(password => {
      credentials.password = password.trim();
      return credentials;
    });
  }


  /**
   * getCredentials
   * get creds from CLI, or security service
   */
  getCredentials(argv)
  {
    return new Promise((res, rej) => {
      if (argv.username && argv.password) {
        res({
          username: argv.username,
          password: argv.password,
        });
      }
      else {
        return this.getSecurityServiceCredentials()
        .then(credentials => res(credentials))
        .catch(e => {
          rej('could not find credentials', e);
        });
      }
    });
  }

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
    // const matrix = fs.readFileSync('Team+vs+module+responsibility+matrix', { encoding: 'UTF-8' });

    const userFromTd = (td) => {
      return td.querySelector ? td.querySelector('a')?.getAttribute('data-username') : null;
    }

    const ths = parse(matrix).querySelectorAll('.confluenceTable tbody th');

    const teams = parse(matrix).querySelectorAll('.confluenceTable tbody tr');
    let pteam = { team: '', po: '', tl: '', github: '', jira: '' };
    teams.forEach((tr, i) => {
      const tds = Array.from(tr.querySelectorAll('td'));
      if (tds.length === ths.length - 1) {
        tds.unshift({ text: '' });
      }
      else if (tds.length === ths.length - 2) {
        tds.unshift({ text: '' });
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

  /**
   * teamForName
   * provide a map from team-name (in the team-project responsibility matrix)
   * to its ID in Jira.
   *
   * astonishingly, custom-field value-lists are not accessible via the API
   * without admin-level access. I don't get it.
   * @param {*} name
   */
  teamForName(name)
  {
    const teams = {
      "@cult": 10304,
      "Concorde": 10571,
      "Core functional team": 10302,
        "Prokopovych (Core: Functional)": 10302,
        "Prokopovych (Core functional) team": 10302,
        "Core: Functional": 10302,
      "Core: Platform": 10432,
        "Core Platform": 10432,
      "EBSCO - FSE": 10307,
      "ERM Subgroup Dev Team": 10308,
        "ERM Delivery": 10308,
      "Falcon": 11327,
      "Firebird": 10883,
        "Firebird team": 10883,
      "Folijet": 10390,
        "Folijet Team": 10390,
      "FOLIO DevOps": 10882,
      "Frontside": 10305,
      "Gulfstream": 10884,
      "Lehigh": 10388,
        "NSIP(Lehigh)": 10388,
      "Leipzig": 10389,
      "Qulto": 10306,
      "Reporting": 11022,
      "Scanbit": 10903,
      "Scout": 11405,
      "Spitfire": 10420,
        "Spitfire Team": 10420,
      "Stacks": 10303,
      "Stripes Force": 10421,
      "Thor": 10609,
      "Thunderjet": 10418,
        "Thunderjet Team": 10418,
      "UNAM": 10309,
      "Vega": 10419,
        "Vega Team": 10419,
      "仁者无敌 \"Benevolence\"": 10909,
      "None": 11025,
    };

    let team = null;

    // even if we _don't_ have a project for the given name, we still
    // resolve, not reject, because we still want to create the ticket;
    // it just won't be assignable to a team.
    return new Promise((resolve, reject) => {
      if (teams[name]) {
        axios.get(`${this.jira}/rest/api/2/customFieldOption/${teams[name]}`)
          .then(res => {
            const team = res.data;
            team.id = `${teams[name]}`;

            resolve(team);
          });
      }
      else {
        console.warn(`Could not match team "${name}"`);
        resolve(null);
      }

    });
  }

  createTicket({summary, description, project, epic, labels, team, cc})
  {
    const body = {
      "fields": {
        "project": { id: project.id },
        summary,
        description,
        issuetype: { id: this.taskType.id },
      }
    };

    if (epic) {
      body.fields.customfield_10002 = epic;
    }

    if (labels) {
      body.fields.labels = labels;
    }

    if (team) {
      body.fields.customfield_10501 = team;
    }

    if (cc && cc.length) {
      const attn = cc.map(i => `[~${i}]`).join(', ');
      body.fields.description += `\n\nAttn: ${attn}`;
    }

    return axios.post(`${this.jira}/rest/api/2/issue`, body, {
      auth: this.credentials,
    });
  }


  linkTicket(inward, outward)
  {
    const body = {
      "outwardIssue": {
        "key": outward.data.key,
      },
      "inwardIssue": {
        "key": inward.data.key,
      },
      "type": this.relatesLink,
    };

    return axios.post(`${this.jira}/rest/api/2/issueLink`, body, {
      auth: this.credentials,
    });
  }


  parseArgv()
  {
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
        alias: 'epic',
        describe: 'jira epic to link to',
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

      .option('password', {
        describe: 'jira password',
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
   * function to each.
   * @arg [] arr array of elements
   * @arg function fn function to apply to each element
   * @return promise
   */
  eachPromise(arr, fn)
  {
    if (!Array.isArray(arr)) return Promise.reject(new Error('Array not found'));
    return arr.reduce((prev, cur) => (prev.then(() => fn(cur))), Promise.resolve());
  };


  async main()
  {
    this.jira = 'https://issues.folio.org';

    // const contents = JSON.parse(fs.readFileSync(filename, { encoding: 'UTF-8'}));
    //
    // jspam --username --password
    //    --link SOME-JIRA -l OTHER-JIRA
    //    --summary "some title"
    //    --description "some description"
    //    --package ./path/to/some/package.json
    try {
      this.argv = this.parseArgv();

      this.credentials = await this.getCredentials(this.argv);

      this.types = await axios.get(`${this.jira}/rest/api/2/issuetype`);
      this.taskType = this.types.data.find(type => type.name === 'Task');

      this.linkTypes = await axios.get(`${this.jira}/rest/api/2/issueLinkType`);
      this.relatesLink = this.linkTypes.data.issueLinkTypes.find(link => link.name === 'Relates');

      this.matrix = await this.getMatrix('https://wiki.folio.org/display/REL/Team+vs+module+responsibility+matrix');

      // get ticket from Jira
      let link;
      if (this.argv.link) {
        link = await axios.get(`${this.jira}/rest/api/2/issue/${this.argv.link}`);
      }

      // map dependencies:
      // @folio/stripes-lib => stripes-lib
      // @folio/some-app => ui-some-app
      // @okapi/some-app => some-app
      const contents = JSON.parse(fs.readFileSync(this.argv.package, { encoding: 'UTF-8'}));
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
        .filter(Boolean);

      // get projects from JIRA
      axios.get(`${this.jira}/rest/api/2/project`)
      .then(projects => {
        // map the array of projects into a hash keyed by name, e.g. ui-some-app
        const pmap = {};
        projects.data.forEach(p => { pmap[p.name] = p; });

        this.eachPromise(deps, d => {
          if (pmap[d]) {
            this.teamForName(this.matrix[d].team)
            .then(team => {
              // only assign the team if we received --team
              const t = this.argv.team ? team : null;
              const cc = [];
              if (this.argv.ccpo && this.matrix[d].po) {
                cc.push(this.matrix[d].po)
              }

              if (this.argv.cctl && this.matrix[d].tl) {
                cc.push(this.matrix[d].tl)
              }

              return this.createTicket({
                summary: this.argv.summary,
                description: this.argv.description,
                project: pmap[d],
                epic: this.argv.epic,
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
            .then((ticket) => {
              console.log(`created ${ticket.data.key} (${d})`)
            })
            .catch(e => {
              console.error(e.response ?? e);
            });
          }
          else {
            console.warn(`could not find a jira project matching ${d}`);
          }
        });
      })
    }
    catch(e) {
      console.error(e);
    };
  }
}

(new JSpam()).main();
