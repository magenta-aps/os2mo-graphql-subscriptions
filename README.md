<!--
SPDX-FileCopyrightText: 2021 Magenta ApS <https://magenta.dk>
SPDX-License-Identifier: MPL-2.0
-->

# OS2mo GraphQL Subscriptions

This repository contains an OS2mo AMQP to GraphQL Subscriptions bridge.

It enables frontends to subscribe to specific changes on objects in OS2mo, and
dynamically react to changes to them as their occur.

## Usage

Adjust the `AMQP_URL` variable to OS2mo's running message-broker, either;
* directly in `docker-compose.yml` or
* by creating a `docker-compose.override.yaml` file.

Now start the container using `docker-compose`:
```
docker-compose up -d
```

You should see the following:
```
[debug    ] Settings fetched               args=() kwargs={} settings=Settings(commit_tag='HEAD', commit_sha='', queue_prefix='os2mo-graphql-subscriptions', log_level=<LogLevel.DEBUG: 10>)
[info     ] Register called                function=callback routing_key=*.*.*
INFO:     Started server process [1]
INFO:     Waiting for application startup.
[info     ] Establishing AMQP connection   host=msg_broker path=/ port=5672 scheme=amqp user=guest
[info     ] Creating AMQP channel
[info     ] Attaching AMQP exchange to channel exchange=os2mo
[info     ] Declaring unique message queue function=callback queue_name=os2mo-graphql-subscriptions_callback
[info     ] Starting message listener      function=callback
[info     ] Binding routing keys           function=callback
[info     ] Binding routing-key            function=callback routing_key=*.*.*
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```
After which a GraphQL interface is exposed at `localhost:8000`.
Now a GraphQL client can subscribe to events with:
```
subscription {
  event_listener(service_type: ORG_UNIT, object_type: WILDCARD, request_type: EDIT, uuid: "1afb982a-7b77-4f1d-ba0d-6da8316d533b") {
    uuid
    object_uuid
    time
  }
}
```
To receive updates on only edit events for any subresource of the organisation unit with uuid: "1afb982a-7b77-4f1d-ba0d-6da8316d533b".

## Development

### Prerequisites

- [Poetry](https://github.com/python-poetry/poetry)

### Getting Started

1. Clone the repository:
```
git clone git@git.magenta.dk:rammearkitektur/os2mo-triggers/os2mo-amqp-trigger-organisation-gatekeeper.git
```

2. Install all dependencies:
```
poetry install
```

3. Set up pre-commit:
```
poetry run pre-commit install
```

### Running the tests

You use `poetry` and `pytest` to run the tests:

`poetry run pytest`

You can also run specific files

`poetry run pytest tests/<test_folder>/<test_file.py>`

and even use filtering with `-k`

`poetry run pytest -k "Manager"`

You can use the flags `-vx` where `v` prints the test & `x` makes the test stop if any tests fails (Verbose, X-fail)

#### Running the integration tests

To run the integration tests, an AMQP instance must be available.

If an instance is already available, it can be used by configuring the `AMQP_URL`
environmental variable. Alternatively a RabbitMQ can be started in docker, using:
```
docker run -d -p 5672:5672 -p 15672:15672 rabbitmq:3-management
```

## Versioning

This project uses [Semantic Versioning](https://semver.org/) with the following strategy:
- MAJOR: Incompatible changes to existing data models
- MINOR: Backwards compatible updates to existing data models OR new models added
- PATCH: Backwards compatible bug fixes

## Authors

Magenta ApS <https://magenta.dk>

## License

This project uses: [MPL-2.0](MPL-2.0.txt)

This project uses [REUSE](https://reuse.software) for licensing.
All licenses can be found in the [LICENSES folder](LICENSES/) of the project.
