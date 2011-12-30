This is the deploy script for mecat-ansto

Prerequisites
    * Download instantclient-basiclite-linux.x64-11.2.0.3.0.zip  instantclient-sdk-linux.x64-11.2.0.3.0.zip from oracle
            http://www.oracle.com/technetwork/topics/linuxx86-64soft-092277.html
    * If using the default install.sh, you must have these files in /root/

Assumptions
    * http_proxy and https_proxy are set (so svn over http, wget, etc. work)
    * cron is installed

Installation
    * Ensure settings_deploy.py and buildout_deploy.cfg are correct for your environment.
    * copy this entire deploy directory to /root/deploy
    * run install.sh as root.  It is recommended you read through the steps yourself to ensure they are correct for your environment.
