const { argv } = require('yargs/yargs')(process.argv.slice(2))
  .usage('Usage: node $0 [options]')
  .example('node $0 -t "RAML 1.0" -f $GH_FOLIO/mod-notes/ramls/note.raml')
  .alias('t', 'type')
  .nargs('t', 1)
  .describe('t', 'The API type: "RAML 1.0" or "OAS 3.0"')
  .alias('f', 'inputFile')
  .nargs('f', 1)
  .describe('f', 'The path of the input file to be processed')
  .demandOption(['t', 'f'])
  .help('h')
  .alias('h', 'help')
  .version('1.0.1');

const amf = require('amf-client-js');
const fs = require('fs');
const path = require('path');

amf.plugins.document.WebApi.register();
amf.plugins.document.Vocabularies.register();
amf.plugins.features.AMFValidation.register();

if (!fs.existsSync(argv.inputFile)) {
  console.error(`Input file does not exist: ${argv.inputFile}`);
  process.exit(1);
}

let validationProfile;
let messageStyles;
switch (argv.type) {
  case 'RAML 1.0':
    validationProfile = amf.ProfileNames.RAML;
    messageStyles = amf.MessageStyles.RAML;
    break;
  case 'OAS 3.0':
    validationProfile = amf.ProfileNames.OAS;
    messageStyles = amf.MessageStyles.OAS;
    break;
  default:
    console.error(`Type '${argv.type}' must be one of 'RAML 1.0' or 'OAS 3.0'.`);
    process.exit(1);
}

const inputExt = path.extname(argv.inputFile);
let mediaType;
switch (inputExt) {
  case '.raml':
    mediaType = 'application/raml';
    break;
  case '.yaml':
    mediaType = 'application/yaml';
    break;
  case '.yml':
    mediaType = 'application/yaml';
    break;
  case '.json':
    mediaType = 'application/json';
    break;
  default:
    console.error('Could not determine media-type from input filename extension.');
    process.exit(1);
}

async function main() {
  await amf.AMF.init();
  const parser = amf.Core.parser(argv.type, mediaType);
  const doc = await parser.parseFileAsync(`file://${argv.inputFile}`);
  let report;
  try {
    report = await amf.AMF.validate(doc, validationProfile, messageStyles);
  } catch (e) {
    process.exitCode = 1;
    console.log(e.toString());
  }
  if (!report.conforms) {
    process.exitCode = 1;
    report.results.map((res) => {
      console.log(`${res.level} - ${res.message}`);
    });
    console.log(report.toString());
  } else {
    console.log('Conforms');
    if (argv.type === 'RAML 1.0') {
      const resolver = amf.Core.resolver('OAS 3.0');
      const resolvedDoc = resolver.resolve(doc, 'compatibility');
      const content = await new amf.Oas30Renderer().generateString(resolvedDoc);
      const outputFn = 'api.yml';
      fs.writeFile(outputFn, content, (err) => {
        if (err) throw err;
        console.log(`Rendered ${outputFn}`);
      });
    }
  }
}

main();
