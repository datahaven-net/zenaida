# zenaida1

Open source domain registry system built on top of EPP protocol



## Contribute

Describe source code and release management flow



## Environment

Make virtual environment

```
$ make venv
```

Activate virtual environment

```
$ source venv/bin/activate
```

Launch Django development server

```
./src/manage.py runserver
```



## Requirements Handling

The project has automated handling of production requirements, the idea behind it is that
you should always use the latest versions of every requirement, a Makefile target is in place
to update the `requirements.txt` file (`make requirements.txt` will do).

In case you need a specific version of a library, the protocol should be:

* Place the needed fixed version using pip notation in any of the requirements/* files
* Put a comment over the fixed requirement explaining the reason for fixing it (usually with a link to an issue/bug)
* Run `make requirements.txt`, the resulting requirements file will include the fixed version of the package

For some more advanced uses, a manual edit of the requirements.txt can be done but make sure to document it somewhere because
`make requirements.txt` *will* overwrite this file.


# Testing against latest versions

By default, `tox` and `make test` will only test against production requirements, in order to test against latest versions of
the dependencies, there are two tox environments, `latest27` and `latest35`.

They can be run via `tox -e latest27,latest35` or also with `make test_latest`


