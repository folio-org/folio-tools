FOLIO Cron Service
===================

The package provides service that will create cronjobs for folio api tasks. 

## Installation

        sudo pip3 install --system git+https://github.com/folio-org/folio-tools.git@FOLIO-3013#egg=folioCronService\&subdirectory=folio-cron-jobs


## Usage

1. Help 

```
$ foliocron --help
usage: foliocron [-h] {service,setup,config} ...

Setup or run service
positional arguments:
  {service,setup,config}
    service             runs okapi api
    setup               Set up crontab to run tasks in config folder
    config              set up credentials

optional arguments:
  -h, --help            show this help message and exit
```

2. `service` subcommand: run a service

```
$ foliocron service --help
usage: foliocron service [-h] [--configDir CONFIGDIR] name

positional arguments:
  name

optional arguments:
  -h, --help            show this help message and exit
  --configDir CONFIGDIR
                        Directory with folioCronService configs, default to system directory
```
                        
3. `setup` subcommand: set up the cron services in the user's crontab

Action creates all FOLIO cron jobs that are configured and enabled within the config folder. The json format and all items are required. 

```
$ foliocron setup --help
usage: foliocron setup [-h] [--configDir CONFIGDIR]

optional arguments:
  -h, --help            show this help message and exit
  --configDir CONFIGDIR
                        Directory with folioCronService configs, default to system directory
```
                        
4. config

Action creates a credential file in HOME directory `~/.foli-cron`

```
$ foliocron config --help
usage: foliocron config [-h] username password

positional arguments:
  username
  password

optional arguments:
  -h, --help  show this help message and exit
```
    

## system wide install
sudo pip3 install --system git+https://github.com/folio-org/folio-tools.git@FOLIO-3013#egg=folioCronService\&subdirectory=folio-cron-jobs
