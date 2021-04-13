## jspam: create jira tickets for many projects

## details

Given a summary and description, and the path to a `package.json`-like
file, create matching JIRA tickets for entries listed as dependencies
that start with `@folio/...` or `@okapi/...`. Optionally:

* create links to existing tickets
* create an epic link
* add labels
* assign a team based on the wiki's team-module matrix
* CC the PO and/or tech lead based on the wiki's team-module matrix

JIRA username and password will be retrieved from the Mac OS keychain entry
`jira-password`, if available; otherwise, they may be passed on the command
line.

## usage

```
jspam --summary <s> --description <d> --link <JIRA-123> --package <package.json>

Options:
  -s, --summary      issue summary (title)                   [string] [required]
  -d, --description  issue description                       [string] [required]
  -p, --package      path to a package.json file to parse    [string] [required]
  -l, --link         jira issue[s] to link to                           [string]
  -e, --epic         jira epic to link to                               [string]
      --label        jira label[s] to apply                             [string]
      --team         assign tickets to teams per team-module-responsibility
                     matrix                                            [boolean]
      --ccpo         CC the product owner per team-module-responsibility matrix
                     in the ticket description                         [boolean]
      --cctl         CC the tech lead per team-module-responsibility matrix in
                     the ticket description                            [boolean]
      --username     jira username                                      [string]
      --password     jira password                                      [string]
  -h, --help         Show help                                         [boolean]
```

## sample output

```
# contents of complete-package.json
{
  "dependencies": {
    "@folio/agreements": ">=1.0.0",
    "@folio/erm-comparisons": ">=1.0.0",
    "@folio/plugin-find-user": ">=1.0.0",
    "@folio/organizations": ">=1.0.0"
  }
}
```

```
$ JDESC=$(cat ./elaborate-summary.txt)
$ node ./jspam.js -s "Update stripes-cli to v2" -d "$JDESC" -l STCLI-169 --package ~/complete-package.json
could not find a jira project matching ui-agreements
could not find a jira project matching ui-erm-comparisons
created UIPFU-38 (ui-plugin-find-user)
created UIORGS-226 (ui-organizations)
```
