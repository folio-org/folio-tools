FOLIO Cron Service
===================

The package provides service that will create cronjobs for folio api tasks. 

### Installation

        sudo pip3 install --system git+https://github.com/folio-org/folio-tools.git@FOLIO-3013#egg=folioCronService\&subdirectory=folio-cron-jobs


### Usage

1. Help 

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

2. config

        $ foliocron config < Username > < password >
    
    Action creates a creadential file in HOME directory `~/.foli-cron`
3. setup

        $ foliocron setup

    Action creates all FOLIO cron jobs that are configured and enabled within the config folder. The json format and all items are required.

        {
            "enable": true,
            "user_config_section":"DEFAULT",
            "cron_time":"*/30 * * * *",
            "tenant": "diku",
            "api-path":"/circulation/scheduled-age-to-lost",
            "method":"POST",
            "data":{}
        }

# system wide install
sudo pip3 install --system git+https://github.com/folio-org/folio-tools.git@FOLIO-3013#egg=folioCronService\&subdirectory=folio-cron-jobs