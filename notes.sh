#!/bin/bash

keyring set https://upload.pypi.org/legacy/ __token__
python3 -m build --sdist .
twine upload --non-interactive dist/pydmart-0.0.5.tar.gz
