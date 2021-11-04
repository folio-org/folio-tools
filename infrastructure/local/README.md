## Purpose

To allow developers to run the infrastructure needed to run FOLIO back end modules locally.

## Infrastructure Included

* PostgreSQL 12
* Kafka

## Prerequisites

* [Docker Compose](https://docs.docker.com/compose/install/)

## Usage

These commands are specific to [Compose V2](https://docs.docker.com/compose/cli-command/#installing-compose-v2),
replace `docker compose` by `docker-compose` if using V1 syntax.

### Starting the infrastructure containers

Run `docker compose up -d`

To only start PostgreSQL run `docker compose up -d postgres`

To only start Kafka use `docker compose up -d kafka`

### Stopping the infrastructure containers

Run `docker compose down`

## Design

### File Structure

A single docker compose file chosen to make it easy to use with limited commands.

