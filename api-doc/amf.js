const fs = require('fs');
const { argv } = require('yargs/yargs')(process.argv.slice(2))
  .usage('Usage: node $0 [options]')
  .example('node $0 -t "RAML 1.0" -m mod-courses -f $GH_FOLIO/mod-courses/ramls/courses.raml')
  .example('node $0 -t "OAS 3.0" -m mod-eusage-reports -f $GH_FOLIO/mod-eusage-reports/src/main/resources/openapi/eusage-reports-1.0.yaml')
  .alias('t', 'type')
  .nargs('t', 1)
  .describe('t', 'The API type: "RAML 1.0" or "OAS 3.0".')
  .alias('f', 'inputFile')
  .nargs('f', 1)
  .describe('f', 'The path of the input file to be processed.')
  .demandOption(['t', 'f'])
  .help('h')
  .alias('h', 'help')
  .version('1.1.0');

const amf = require('amf-client-js');

if (!fs.existsSync(argv.inputFile)) {
  console.error(`Input file does not exist: ${argv.inputFile}`);
  process.exit(1);
}

let client;
switch (argv.type) {
  case 'RAML 1.0':
    client = amf.RAMLConfiguration.RAML10().baseUnitClient();
    break;
  case 'OAS 3.0':
    client = amf.OASConfiguration.OAS30().baseUnitClient();
    break;
  default:
    console.error(`Type '${argv.type}' must be one of 'RAML 1.0' or 'OAS 3.0'.`);
    process.exit(1);
}

async function main() {
  const parsingResult = await client.parseDocument(`file://${argv.inputFile}`);
  const endpoints = [];
  if (parsingResult.conforms) {
    process.exitCode = 0;
    const transformed = client.transform(parsingResult.baseUnit);
    const doc = transformed.baseUnit;
    const api = doc.encodes;
    api.endPoints.forEach((endpoint) => {
      const methods = [];
      let serversCount = null;
      let server0Url = '';
      if (endpoint.operations[0]) {
        serversCount = endpoint.operations[0].servers.length;
      }
      if (serversCount) {
        server0Url = `${endpoint.operations[0].servers[0].url}`;
        if (server0Url.startsWith('http')) {
          server0Url = '';
        }
      }
      endpoint.operations.forEach((operation) => {
        const op = `${operation.method}:${operation.operationId}`;
        methods.push(op.replace(/ /g, '_'));
      });
      const epPath = `${server0Url}${endpoint.path}`;
      if (methods.length) {
        const ep = {
          path: `${epPath.replace(/\/\//, '/')}`,
          methods: `${methods.sort().join(' ')}`,
          apiDescription: `${argv.inputFile}`,
        };
        endpoints.push(ep);
      }
    });
  } else {
    process.exitCode = 1;
  }
  console.log(JSON.stringify(endpoints, null, 2));
}

main();
