"""
## Multiple platform selector for pyOpenSSL binary distributions
# Original from: https://pypi.python.org/pypi/pyOpenSSL/0.13
# Note: Version 0.14 switches to pure python relying on cryptographic
#  library which relies on cffi (amongst other things). A similar
#  pattern to this could probably be followed for it's binary
#  modules if and upgrade is ever required.

## To add new platform:
# Ensure python compatible toolchain is installed
# extract pyOpenSSL-0.13.tar.gz
# Ensure you run the same version of python used in kodi on your platform.

cd pyOpenSSL-0.13
python -c "import setuptools; execfile('setup.py')" bdist_egg
cp dist/pyOpenSSL-0.13-*.egg ../
cd ../
for filename in *.egg; do
 mkdir "${filename%.*}"
 unzip $filename -d "${filename%.*}"
 rm $filename
done
python __init__.py

# This will print out the identifier matches on the current system
# add a suitable identifier match -> new folder path below
# Please do contribute added distributions back to project!
"""

import os
import sys
import platform

path = None

identifier1 = (platform.system(), platform.architecture()[0]) + platform.python_version_tuple()[0:2]
identifier2 = None

## Platform Identifiers
identifier1_matches = {
    ('Darwin', '64bit', '2', '6')  : "pyOpenSSL-0.13-py2.6-macosx-10.10-intel",
    ('Windows', '32bit', '2', '6') : "pyOpenSSL-0.13-py2.6-win32",
    ('Windows', '32bit', '2', '7') : "pyOpenSSL-0.13-py2.7-win32",
    ('Windows', '64bit', '2', '7') : "pyOpenSSL-0.13-py2.7-win64",
}

if identifier1 in identifier1_matches:
    path = os.path.join(os.path.dirname(__file__), identifier1_matches[identifier1])

elif 'Linux' in identifier1:
    identifier2 = identifier1 + platform.libc_ver()

    identifier2_matches = {
       ('Linux', '64bit', '2', '7', 'glibc', '2.4'): "pyOpenSSL-0.13-py2.7-linux-x86_64"
    }

    if identifier2 in identifier2_matches:
        path = os.path.join(os.path.dirname(__file__), identifier2_matches[identifier2])

if not path:
    print "OpenSSL distribution not available for your platform. \nPlease add one if possible by following instructions in top of file: " + str(__file__)
    print "iDENTIFIED PLATFORM: %s" % str(identifier1)
else:
    # Add required paths to python search path
    if path not in sys.path:
        sys.path.append(path)

import OpenSSL

if __name__ == "__main__":
    print "identifier1 = " + str(identifier1)
    if identifier2:
        print "identifier2 = " + str(identifier2)
