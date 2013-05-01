
TEMPLATE=backend_sql.template
if [ ! -e $TEMPLATE ]; then 
    echo "Cannot find file $TEMPLATE" 
    exit
fi

case $1 in 
    "p" | "pg" | "postgres" ) 
        NAME=postgres
        export PGPASSWORD=postgres
        psql -U postgres -c "DROP DATABASE keystonetest"
        psql -U postgres -c "CREATE DATABASE keystonetest"
        CONNECTION="postgresql://keystone:keystone@localhost/keystonetest?client_encoding=utf8"
        unset PGPASSWORD
        ;;
    "m" | "my" | "mysql" ) 
        NAME=mysql
        mysql -uroot -ptest -e "DROP DATABASE keystonetest; CREATE DATABASE keystonetest"
        CONNECTION="mysql://root:test@localhost/keystonetest?charset=utf8"
        ;;
    "s" | "sqlite" ) 
        NAME=sqlite
        CONNECTION="sqlite://"
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

tty -s

# TESTNAME=
# if [ ! -z $2 ]; then
# # test_sql_upgrade:SqlUpgradeTests
#     TESTNAME=$2
# fi

nosetests --openstack-stdout $@ # 2>&1 | tee test_$NAME.log test_last.log
