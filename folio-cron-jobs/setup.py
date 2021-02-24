from setuptools import setup, find_packages

setup(name='folioCronService',
      version='1.0',
      packages=find_packages(),
      install_requires=[
          'requests',
          'python-crontab',
      ],
      scripts=['foliocronservice'],
      package_data={'': ['config/*.json']},
      include_package_data=True,
      )