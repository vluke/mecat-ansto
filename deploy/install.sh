set -u
set -e

echo "This script has manual steps and will prompt you"
echo "Press enter to continue..."
read

#WARN: do not use spaces in these...
UNPACK_HOME=/root/deploy #you will need to edit buildout.cfg if you change this
MECAT_HOME=/opt/mecat
MECAT_ANSTO=$MECAT_HOME/mecat-ansto
DJANGO=$MECAT_ANSTO/bin/django
 
TOMCAT_HOME=/usr/local/tomcat6

#some defaults
yum install subversion python26 cyrus-sasl-ldap cyrus-sasl-devel openldap-devel libxslt libxslt-devel libxslt-python python26-devel gcc openssl-devel httpd python26-mod_wsgi java-1.6.0-openjdk java-1.6.0-openjdk-devel
/sbin/chkconfig httpd on

/sbin/service httpd start

#prepare home directory
mkdir $MECAT_HOME
chmod 755 $MECAT_HOME

# checkout code
svn co http://mytardis.googlecode.com/svn/apps/mecat-ansto/tags/mecat-ansto-dec2011 $MECAT_ANSTO

cd $MECAT_ANSTO
python26 bootstrap.py
cp -f $UNPACK_HOME/buildout_deploy.cfg $MECAT_ANSTO/buildout_deploy.cfg
echo "copy instantclient files to /root/"
echo "press enter when done"
read
cd $MECAT_ANSTO
./bin/buildout -c buildout_deploy.cfg

echo "$MECAT_ANSTO/parts/python-oracle/" > /etc/ld.so.conf.d/oracle.conf
/sbin/ldconfig

# set permissions of directories defined in buildout
mkdir /var/mytardis/log
chown -R apache:apache /var/mytardis/{store,staging,oai,log}

cp -f $UNPACK_HOME/settings_deploy.py $MECAT_ANSTO/mecat/settings_deploy.py
#prepare database
$DJANGO syncdb --noinput  # ignore warnings about indexes at the end

echo "Schema.objects.all().delete()" | $DJANGO shell_plus # deletes initial (AS-specific) fixtures
#load schemas
$DJANGO loadschemas $MECAT_ANSTO/src/ands_register/ands_register/fixtures/ands_register_schema.json
$DJANGO loadschemas $MECAT_ANSTO/src/related_info/related_info/fixtures/related_schemas.json
$DJANGO loadschemas $UNPACK_HOME/ansto_schemas.json

#creating seed data
$DJANGO createembargopermission
$DJANGO createtokenuser
echo "manual step"
echo "press enter to continue"
read
$DJANGO createsuperuser

# add http to https redirect
cp $UNPACK_HOME/httpd.conf.add /etc/httpd/conf.d/https_redirect.conf

#add cronjobs
crontab $UNPACK_HOME/cronjobs.txt

# single search/SOLR
echo "MANUAL STEP! edit $MECAT_ANSTO/mecat/settings_deploy.py SINGLE_SEARCH_ENABLED=True"
echo "Press enter to continue..."
read
tar xvzf $UNPACK_HOME/apache-solr-1.4.1.tgz -C $UNPACK_HOME
tar xvzf $UNPACK_HOME/apache-tomcat-6.0.33.tar.gz -C $UNPACK_HOME

mkdir -p `dirname $TOMCAT_HOME`
cp -r $UNPACK_HOME/apache-tomcat-6.0.33 $TOMCAT_HOME/
cp -r $UNPACK_HOME/apache-solr-1.4.1/example/solr/ $TOMCAT_HOME/solr
mkdir -p $TOMCAT_HOME/conf/Catalina/localhost/
cp $UNPACK_HOME/solr.xml $TOMCAT_HOME/conf/Catalina/localhost/solr.xml
cp $UNPACK_HOME/apache-solr-1.4.1/dist/apache-solr-1.4.1.war $TOMCAT_HOME/webapps/solr.war

cd $TOMCAT_HOME/bin
tar xvf commons-daemon-native.tar.gz
cd commons-daemon-1.0.7-native-src/unix
autoconf && ./configure --with-java=/usr/lib/jvm/java-1.6.0-openjdk.x86_64/ && make

#jOAI
unzip $UNPACK_HOME/joai_v3.1.1.zip
cp $UNPACK_HOME/joai_v3.1.1/oai.war $TOMCAT_HOME/webapps
cp $UNPACK_HOME/tomcat6 /etc/init.d/tomcat6
/sbin/chkconfig tomcat6 on
/sbin/service tomcat6 start

cp $UNPACK_HOME/proxy_ajp.conf /etc/httpd/conf.d/
cp $UNPACK_HOME/python26-mod_wsgi.conf /etc/httpd/conf.d/

/sbin/service httpd restart

cp $UNPACK_HOME/tomcat-users.xml $TOMCAT_HOME/conf/tomcat-users.xml
echo 'uncomment the comment starting just before security-constraint in "$TOMCAT_HOME/webapps/oai/WEB-INF/web.xml"'
echo 'change the username/password in $TOMCAT_HOME/conf/tomcat-users.xml for role oai_admin'
echo 'press enter to continue'
read

/sbin/service tomcat6 stop && /sbin/service tomcat6 start

# manual OAI setup
echo "setup OAI by visiting http://localhost/oai"
echo "data provider > repository information and administration"
echo "Name: ANSTO MyTARDIS"
echo "administrator e-mail: ryan@ryan.ryan"
echo "description: ANSTO tardis-test OAI-PMH/RIF-CS Server"
echo "Identifier: tardis-test.nbi.ansto.gov.au"
echo "Press enter to continue..."
read
echo "data provider > metadata files configuration > add metadata directory"
echo "Name: tardis-test rif-cs"
echo "Format of files: rif"
echo "Path: /var/mytardis/oai/"
echo "Press enter to continue..."
read

cp $UNPACK_HOME/.netrc /root/.netrc
echo 'edit $TOMCAT_HOME/solr/conf/solrconfig.xml dataDir
  <dataDir>${solr.data.dir:./solr/data}</dataDir>
  <dataDir>${solr.data.dir:/var/solr/data}</dataDir>
'
echo 'press enter to continue..'
read

/sbin/service tomcat6 stop && /sbin/service tomcat6 start

cp $UNPACK_HOME/update-solr-schema.sh $MECAT_ANSTO/src/MyTARDIS/utils/update-solr-schema.sh

$MECAT_ANSTO/src/MyTARDIS/utils/update-solr-schema.sh

echo "Done"
