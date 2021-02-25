
import requests
from crontab import CronTab
try:
    import configparser
except:
    import ConfigParser
import copy, json, os, sys
import argparse 

opaki_url = os.getenv('OKAPI_URL', 'http://localhost:9130')
header_default={ "Content-type": "application/json", "cache-control": "no-cache", "accept": "application/json" }

def getCredentials(section="DEFAULT"):
    """ 
        getCredentials- pull credentials from credential file.
    """
    home=os.path.expanduser('~')
    credentials="{0}/.folio-cron".format(home)
    try:
        config = configparser.ConfigParser()
    except:
        config = ConfigParser.ConfigParser()
    config.read(credentials)
    return  dict(config.items(section))

def getAuthToken(tenant,section="DEFAULT"):
    """ 
        getAuthToken- returns auth token.
    """
    headers = copy.copy(header_default)
    headers["x-okapi-tenant"]= tenant
    creds= getCredentials(section)
    req = requests.post("{0}/authn/login".format(opaki_url),data=json.dumps(creds),headers=headers)
    if req.status_code >= 400:
        raise Exception("Please check username and password in credential file ('~/.folio-cron').")
    return req.headers['x-okapi-token']

def getServiceVariables(name):
    """ 
        getServiceVariables- return cron config service variables.
    """
    path=os.path.dirname(os.path.abspath(__file__))
    with open("{0}/config/{1}.json".format(path,name),'r') as f1:
        jsonstring=f1.read()
    return json.loads(jsonstring)

def cronOkapiService(name,**kwargs):
    """ 
        cronOkapiService - The service witch allows Okapi POST or GET.
    """
    service_vars = getServiceVariables(name)
    headers = copy.copy(header_default)
    headers["x-okapi-tenant"]= service_vars['tenant']
    headers["x-okapi-token"]=getAuthToken(service_vars['tenant'],section=service_vars['user_config_section'])
    if service_vars['method'].lower() == 'post':
        payload=service_vars['data']
        req = requests.post("{0}{1}".format(opaki_url,service_vars['api-path']), data=json.dumps(payload),headers=headers)
        
    elif service_vars['method'].lower() == 'get':
        payload=service_vars['data']
        req = requests.get("{0}{1}".format(opaki_url,service_vars['api-path']), params=payload,headers=headers)
        print(req.json())
    else:
        raise Exception("Method not supported(Only GET and POST)")

def cronOkapiServiceSetup(**kwargs):
    """ 
        cronOkapiServiceSetup - provide the set up of all enabled cronjobs within the config folder.
    """
    path="{0}/config".format(os.path.dirname(os.path.abspath(__file__)))
    _, _, filenames = next(os.walk(path))
    home=os.path.expanduser('~')
    crontab_template = "{0} export OKAPI_URL={1};{2} service {3} >> {4}/folio_cron_output.log 2>&1"
    cron = CronTab()
    cron = CronTab(user=True)
    cron.read()
    cron_jobs = cron.__str__().split('\n')
    cron.remove_all()
    abspath = os.path.abspath(__file__)
    abspath = "{0}bin/foliocron".format(abspath.split('lib')[0])
    for filename in filenames:
        job=os.path.splitext(filename)
        if job[1]=='.json':
            service_vars=getServiceVariables(job[0])
            if service_vars['enable']:
                crontab_string = crontab_template.format(service_vars['cron_time'],opaki_url,abspath,job[0],home)
                cron_jobs.append(crontab_string)
    cron_jobs=list(set(cron_jobs))
    cron_jobs.remove("")
    crontab_string= "\n".join(cron_jobs)
    cron = CronTab(tab=crontab_string)
    cron.write_to_user()

def cronConfig(username,password,**kwargs):
    """ 
        cronConfig - creates auth file in home directory. Only sets the DEFAULT config section.
    """
    home=os.path.expanduser('~')
    filename = "{0}/.folio-cron".format(home)  
    try:
        config = configparser.ConfigParser()
    except:
        config = ConfigParser.ConfigParser()     
    config['DEFAULT'] = {'username': username,'password':password} 
    with open(filename, 'w') as configfile:
        config.write(configfile)
    