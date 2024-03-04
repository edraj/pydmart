# Pydmart

This is a Python Dmart client used to interact with a Dmart instance


## Installation

Pydmart is distributed via [PyPI](https://pypi.org/project/pydmart/):

```python
pip install pydmart
```

## Example

Just two steps and you will be ready to interact with your Dmart instance

1. instantiate an object `d_client = DmartService({dmart_instance_url, username, password})`
2. connect the client to the Dmart instance and authenticate your user `await d_client.connect()`

then you will be able to retrieve your profile as simple as this
`await d_client.get_profile()`