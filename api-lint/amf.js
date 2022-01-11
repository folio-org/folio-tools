const { argv } = require('yargs/yargs')(process.argv.slice(2))
  .usage('Usage: node $0 [options]')
  .example('node $0 -t "RAML 1.0" -f $GH_FOLIO/mod-courses/ramls/courses.raml')
  .example('node $0 -t "OAS 3.0" -f $GH_FOLIO/mod-eusage-reports/src/main/resources/openapi/eusage-reports-1.0.yaml')
  .alias('t', 'type')
  .nargs('t', 1)
  .describe('t', 'The API type: "RAML 1.0" or "OAS 3.0".')
  .alias('f', 'inputFile')
  .nargs('f', 1)
  .describe('f', 'The path of the input file to be processed.')
  .alias('w', 'warnings')
  .describe('w', 'Cause "warnings" to fail the workflow,\nin the absence of "violations".')
  .demandOption(['t', 'f'])
  .help('h')
  .alias('h', 'help')
  .version('1.1.0');

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
  const validationResult = await client.validate(parsingResult.baseUnit);
  console.log('---- Summary:');
  console.log(`parsingResult.conforms: ${parsingResult.conforms}`);
  console.log(`parsingResult.results.length: ${parsingResult.results.length}`);
  parsingResult.results.forEach((res) => {
    console.log(`${res.severityLevel}: ${res.message}`);
  });
  console.log('--------');
  console.log(`validationResult.conforms: ${validationResult.conforms}`);
  console.log(`validationResult.results.length: ${validationResult.results.length}`);
  validationResult.results.forEach((res) => {
    console.log(`${res.severityLevel}: ${res.message}`);
  });
  console.log('--------\n');
  console.log('---- parsingResult:');
  console.log(parsingResult.toString());
  console.log('---- validationResult:');
  console.log(validationResult.toString());
  if (!parsingResult.conforms || !validationResult.conforms) {
    process.exitCode = 1;
  }
  if (argv.warnings) {
    if (parsingResult.conforms && (parsingResult.results.length > 0)) {
      process.exitCode = 1;
    }
    if (validationResult.conforms && (validationResult.results.length > 0)) {
      process.exitCode = 1;
    }
  }
}

main();
