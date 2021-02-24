from setuptools import setup, find_packages

setup(name='folioCronService',
      version='1.0',
      packages=find_packages(),
      install_requires=[
          'requests',
          'python-crontab',
      ],
      scripts=['foliocron'],
      #data_files=[('config', ['*.json']),]
      package_data={'folioCronService': ['config/*.json']},
      include_package_data=True,
      )