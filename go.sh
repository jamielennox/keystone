
TEMPLATE=backend_sql.template
if [ ! -e $TEMPLATE ]; then
    echo "Cannot find file $TEMPLATE"
    exit
fi

KEYSTONEDBSERVER=localhost
KEYSTONEUSER=keystonetest
KEYSTONEPASS=keystonetest
KEYSTONEDB=keystonetest

case $1 in
    "p" | "pg" | "postgres" )
        NAME=postgres

        # CREATE USER keystonetest WITH PASSWORD 'keystonetest';
        # CREATE DATABASE keystonetest;
        # GRANT ALL PRIVILEGES ON DATABASE keystonetest TO keystonetest;

        export PGPASSWORD=$KEYSTONEPASS
        psql -U $KEYSTONEUSER -c "select 'drop table \"' || tablename || '\" cascade;' from pg_tables;" > /dev/null || { echo "Failed to clear database"; exit 1; }
        CONNECTION="postgresql://$KEYSTONEUSER:$KEYSTONEPASS@$KEYSTONEDBSERVER/$KEYSTONEDB?client_encoding=utf8"
        unset PGPASSWORD
        ;;
    "m" | "my" | "mysql" )
        NAME=mysql

        # CREATE USER keystonetest;
        # CREATE DATABASE keystonetest;
        # grant all on keystonetest.* to keystonetest@localhost identified by 'keystonetest'

        TABLES=`mysql -u$KEYSTONEUSER -p$KEYSTONEPASS --batch --skip-column-names -e "SELECT concat('DROP TABLE IF EXISTS ', table_name, ';') FROM information_schema.tables WHERE table_schema = '$KEYSTONEDB'"`
        if [ -n "$TABLES" ]; then
            mysql -u$KEYSTONEUSER -p$KEYSTONEPASS -D $KEYSTONEDB -e "SET FOREIGN_KEY_CHECKS = 0; $TABLES SET FOREIGN_KEY_CHECKS = 1;"
        fi
        CONNECTION="mysql://$KEYSTONEUSER:$KEYSTONEPASS@$KEYSTONEDBSERVER/$KEYSTONEDB?charset=utf8"
        ;;
    "s" | "sqlite" )
        NAME=sqlite
        CONNECTION="sqlite://"
        ;;
    "f" | "file" )
        NAME=file
        CONNECTION="sqlite:///keystone.db"
        ;;
    "a" | "all" )
        echo "*** SQLITE ***"
        $0 sqlite $2
        echo "*** MYSQL ***"
        $0 mysql $2
        echo "*** POSTGRES ***"
        $0 postgres $2
        echo "*** DONE ***"
        exit
        ;;
    * )
        echo "Please pick postgres, mysql or sqlite for first parameter"
        exit
        ;;
esac

shift
sed -e "s;%CONNECTION%;$CONNECTION;" $TEMPLATE > tests/backend_sql.conf

rm -rf vendor/*

# TESTNAME=
# if [ ! -z $2 ]; then
# # test_sql_upgrade:SqlUpgradeTests
#     TESTNAME=$2
# fi

nosetests -s --openstack-stdout $@ # 2>&1 | tee test_$NAME.log test_last.log

git checkout tests/backend_sql.conf
