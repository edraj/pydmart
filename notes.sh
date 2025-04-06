#!/bin/bash

#keyring set https://upload.pypi.org/legacy/ __token__
pip wheel .
python3 -m build
python3 -m build --sdist .
twine upload --non-interactive dist/pydmart-1.0.7.tar.gz
twine upload --non-interactive dist/pydmart-1.0.7-py3-none-any.whl
