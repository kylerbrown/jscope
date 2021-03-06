from __future__ import print_function
from setuptools import setup
from setuptools.command.test import test as TestCommand
import io
import os
import sys

import jscope

here = os.path.abspath(os.path.dirname(__file__))

def read(*filenames, **kwargs):
    encoding = kwargs.get('encoding', 'utf-8')
    sep = kwargs.get('sep', '\n')
    buf = []
    for filename in filenames:
        with io.open(filename, encoding=encoding) as f:
            buf.append(f.read())
    return sep.join(buf)

long_description = read('README.md')

class PyTest(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        import pytest
        errcode = pytest.main(self.test_args)
        sys.exit(errcode)

setup(
    name='jscope',
    script='jscope/jscope.py',
    version=jscope.__version__,
    url='http://github.com/kylerbrown/jscope/',
    license='MIT License',
    author='Kyler Brown',
    tests_require=['pytest'],
    install_requires=['pyjack>=0.5.2',
                      'pyqtgraph>=0.9.7',
                      'numpy>=1.7.1',
                      'PySide>=1.2.1'
                    ],
    dependency_links = [
        'http://downloads.sourceforge.net/project/py-jack/py-jack/0.5.2/pyjack-0.5.2.tar.gz'
    ],
    cmdclass={'test': PyTest},
    author_email='kylerjbrown@gmail.com',
    description='A scrolling oscilloscope for the JACK audio framework',
    long_description=long_description,
    packages=['jscope'],
    include_package_data=True,
    platforms='any',
    test_suite='jscope.test.test_jscope',
    classifiers = [
        'Programming Language :: Python',
        'Development Status :: 4 - Beta',
        'Natural Language :: English',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Topic :: Scientific/Engineering',
        ],
    extras_require={
        'testing': ['pytest'],
    }
)
