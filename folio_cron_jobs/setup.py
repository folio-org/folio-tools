from setuptools import setup, find_packages

setup(name='folioCronService',
      version='1.0',
      packages=find_packages(),
      install_requires=[
          'requests',
          'python-crontab',
      ],
      scripts=['folio_cron_jobs/folioCronService'],
      package_data={'': ['folio_cron_jobs/config/*.json']},
      include_package_data=True,
      )