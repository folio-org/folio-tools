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
  .version('1.0.0');

const amf = require('amf-client-js');
const fs = require('fs');

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
      endpoint.operations.forEach((operation) => {
        methods.push(operation.method);
      });
      if (methods.length) {
        const ep = {
          path: `${endpoint.path}`,
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
