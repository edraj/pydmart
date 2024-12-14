# Pydmart

This is a Python Dmart client used to interact with a Dmart instance


## Installation

Pydmart is distributed via [PyPI](https://pypi.org/project/pydmart/):

```python
pip install pydmart2
```

## Example

Just simple steps and you will be ready to interact with your Dmart instance

1. import the class `from pydmart.dmart_service import DmartService`
2. instantiate an object `d_client = DmartService({dmart_instance_url}, {username}, {password})`
3. Create / delete connection pool : Preferably in global fastapi lifespan (async)
4. connect the client to the Dmart instance and authenticate your user `await d_client.connect()`


You will be able to retrieve your profile as simple as 
`await d_client.get_profile()`
