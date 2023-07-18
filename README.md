# g2configtool

## Overview

This Dockerfile is a wrapper over Senzing's G2ConfigTool.py.

### Contents

1. [Expectations](#expectations)
1. [Demonstrate using Docker](#demonstrate-using-docker)
    1. [Configuration](#configuration)
    1. [Volumes](#volumes)
    1. [Database support](#database-support)
    1. [Run docker container](#run-docker-container)
1. [References](#references)

### Legend

1. :thinking: - A "thinker" icon means that a little extra thinking may be required.
   Perhaps you'll need to make some choices.
   Perhaps it's an optional step.
1. :pencil2: - A "pencil" icon means that the instructions may need modification before performing.
1. :warning: - A "warning" icon means that something tricky is happening, so pay attention.

## Expectations

- **Space:** This repository and demonstration require 1 GB free disk space.
- **Time:** Budget 40 minutes to get the demonstration up-and-running, depending on CPU and network speeds.
- **Background knowledge:** This repository assumes a working knowledge of:
  - [Docker](https://github.com/Senzing/knowledge-base/blob/main/WHATIS/docker.md)

## Demonstrate using Docker

### Configuration

Configuration values specified by environment variable or command line parameter.

- **[SENZING_DEBUG](https://github.com/Senzing/knowledge-base/blob/main/lists/environment-variables.md#senzing_debug)**

### Volumes

1. :pencil2: Specify the directory containing the Senzing installation.
   Example:

    ```console
    export SENZING_VOLUME=/opt/my-senzing
    ```

    1. :warning:
       **macOS** - [File sharing](https://github.com/Senzing/knowledge-base/blob/main/HOWTO/share-directories-with-docker.md#macos)
       must be enabled for `SENZING_VOLUME`.
    1. :warning:
       **Windows** - [File sharing](https://github.com/Senzing/knowledge-base/blob/main/HOWTO/share-directories-with-docker.md#windows)
       must be enabled for `SENZING_VOLUME`.

1. Identify the `data_version`, `etc`, `g2`, and `var` directories.
   Example:

    ```console
    export SENZING_ETC_DIR=${SENZING_VOLUME}/etc
    ```

### Database support

:thinking: **Optional:**  Some database need additional support.
For other databases, these steps may be skipped.

1. **Db2:** See
   [Support Db2](https://github.com/Senzing/knowledge-base/blob/main/HOWTO/support-db2.md)
   instructions to set `SENZING_OPT_IBM_DIR_PARAMETER`.
1. **MS SQL:** See
   [Support MS SQL](https://github.com/Senzing/knowledge-base/blob/main/HOWTO/support-mssql.md)
   instructions to set `SENZING_OPT_MICROSOFT_DIR_PARAMETER`.

### Run docker container

1. Run docker container.
   Example:

    ```console
    sudo docker run \
      --interactive \
      --rm \
      --tty \
      --volume ${SENZING_ETC_DIR}:/etc/opt/senzing \
      ${SENZING_OPT_IBM_DIR_PARAMETER} \
      ${SENZING_OPT_MICROSOFT_DIR_PARAMETER} \
      senzing/g2configtool \
        --iniFile /etc/opt/senzing/G2Project.ini \
        --g2ConfigFile /etc/opt/senzing/g2config.json \
        --g2VariantFile /etc/opt/senzing/cfgVariant.json
    ```

## References

- [Development](docs/development.md)
- [Errors](docs/errors.md)
- [Examples](docs/examples.md)
- Related artifacts
  - [DockerHub](https://hub.docker.com/r/senzing/g2configtool)
