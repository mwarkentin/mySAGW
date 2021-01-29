# mySAGW

!!!WIP!!!

[![Build Status](https://github.com/adfinis-sygroup/mySAGW/workflows/Tests/badge.svg)](https://github.com/adfinis-sygroup/mySAGW/actions?query=workflow%3ATests)
[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen.svg)](https://github.com/adfinis-sygroup/mySAGW/blob/master/api/setup.cfg#L53)
[![Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/adfinis-sygroup/mySAGW)
[![License: GPL-3.0-or-later](https://img.shields.io/github/license/adfinis-sygroup/mySAGW)](https://spdx.org/licenses/GPL-3.0-or-later.html)

Application management for SAGW

## Getting started

### Installation (dev)

**Requirements**
* docker
* docker-compose

After installing and configuring those, download [docker-compose.yml](https://raw.githubusercontent.com/adfinis-sygroup/mysagw/master/docker-compose.yml) and run the following command:

```bash
echo "UID=$(id -u)" > .env
docker-compose up -d
```

Load the config data into Caluma:

```bash
make caluma-loadconfig
```

Add `mysagw.local` to `/etc/hosts`:

```bash
echo "127.0.0.1 mysagw.local" | sudo tee -a /etc/hosts
```

You can now access the application under the following URIs:

 - https://mysagw.local/ --> frontend
 - https://mysagw.local/auth/ --> keycloak
 - https://mysagw.local/api/ --> backend
 - https://mysagw.local/graphql/ --> caluma

### Configuration

mySAGW is a [12factor app](https://12factor.net/) which means that configuration is stored in environment variables.
Different environment variable types are explained at [django-environ](https://github.com/joke2k/django-environ#supported-types).


### Deployment

```bash
cp -r ./.envs/.production.example ./.envs/.production
```

Then edit the files under `./.envs/.production/` to your needs.

```bash
echo "UID=$(id -u)" > .env
docker-compose up -d
make caluma-loadconfig
```

## Contributing

Look at our [contributing guidelines](CONTRIBUTING.md) to start with your first contribution.
