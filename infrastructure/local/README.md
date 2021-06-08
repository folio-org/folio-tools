## Purpose

To allow developers to run the infrastructure needed to run FOLIO back end modules locally.

## Infrastructure Included

* PostgreSQL 10
* Kafka

## Prerequisites

* [Docker Desktop](https://www.docker.com/products/docker-desktop)

## Usage

These commands are specific to later versions of Docker where compose is part of the main CLI

### Starting the infrastructure containers

Run `docker compose up -d`

### Stopping the infrastructure containers

Run `docker compose down`

## Design

### File Structure

A single docker compose file chosen to make it easy to use with limited commands. 

A trade off with this approach is that it does not provide the flexibility to only 
run part of the infrastructure that a particular module uses. 

This could be addressed by separating the file by part of the infrastructure e.g. PostgreSQL, Kafka  