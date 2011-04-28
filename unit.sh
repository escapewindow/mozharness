#!/bin/sh
###########################################################################
# This requires coverage and nosetests:
#
#  easy_install nose
#  easy_install coverage
###########################################################################

export PYTHONPATH=.:..:$PYTHONPATH
echo "### Running pylint"
pylint -E -e F -f parseable `find mozharness -name [a-z]\*.py` `find scripts -name [a-z]\*.py`

rm -rf upload_dir
echo "### Testing non-networked unit tests"
coverage run -a --branch --omit='/Library/*,/usr/*,/opt/*' `which nosetests` test/test_*.py
echo "### Testing networked unit tests"
coverage run -a --branch --omit='/Library/*,/usr/*,/opt/*' `which nosetests` test/networked/test_*.py
echo "### Running *.py [--list-actions]"
for filename in `find mozharness -name [a-z]\*.py`; do
  coverage run -a --branch --omit='/Library/*,/usr/*,/opt/*' $filename
done
for filename in `find scripts -name [a-z]\*.py` ; do
  coverage run -a --branch --omit='/Library/*,/usr/*,/opt/*' $filename --list-actions | grep -v "Actions available" | grep -v "Default actions"
done
echo "### Running scripts/configtest.py --log-level warning"
coverage run -a --branch --omit='/Library/*,/usr/*,/opt/*' scripts/configtest.py --log-level warning
rm -rf upload_dir

echo "### Creating coverage html"
coverage html --omit="/Library/*,/usr/*,/opt/*" -d coverage.new
if [ -e coverage ] ; then
    mv coverage coverage.old
    mv coverage.new coverage
    rm -rf coverage.old
else
    mv coverage.new coverage
fi
