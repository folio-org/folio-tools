const amf = require('amf-client-js');
const fs = require('fs');
const path = require('path');

amf.plugins.document.WebApi.register();
amf.plugins.document.Vocabularies.register();
amf.plugins.features.AMFValidation.register();

const amfType = process.argv[2];
const inputFn = process.argv[3];

if (!fs.existsSync(inputFn)) {
  console.error(`Input file does not exist: ${inputFn}`);
  process.exit(1);
}

let validationProfile;
let messageStyles;
switch (amfType) {
  case 'RAML 1.0':
    validationProfile = amf.ProfileNames.RAML;
    messageStyles = amf.MessageStyles.RAML;
    break;
  case 'OAS 3.0':
    validationProfile = amf.ProfileNames.OAS;
    messageStyles = amf.MessageStyles.OAS;
    break;
  default:
    console.error(`Type '${amfType}' must be one of 'RAML 1.0' or 'OAS 3.0'.`);
    process.exit(1);
}

const inputExt = path.extname(inputFn);
let mediaType;
switch (inputExt) {
  case '.raml':
    mediaType = 'application/raml';
    break;
  case '.yaml':
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
  const parser = amf.Core.parser(amfType, mediaType);
  const doc = await parser.parseFileAsync(`file://${inputFn}`);
  let report;
  try {
    report = await amf.AMF.validate(
      doc, validationProfile, messageStyles,
    );
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
  }
}

main();
