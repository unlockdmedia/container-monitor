#!/usr/bin/env python
#
# Monitor container health

from __future__ import print_function
import argparse
import os
import time
import datetime
from collections import Counter
import docker
import datadog

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--interval', default=60, help='Number of seconds between each poll')
    parser.add_argument('--short-lived', dest='short_lived', default=300, help='Number of lifespan seconds to be consider short-lived containers')
    parser.add_argument('--statsd-host', dest='statsd_host', help='Statsd host. if not specified, will fallback to STATSD_HOST, then localhost')
    parser.add_argument('--statsd-port', dest='statsd_port', default=8125, help='Statsd port')
    parser.add_argument('--metric-prefix', dest='metric_prefix', default="container_health", help='Datadog Metrics name prefix')
    return parser.parse_args()

def log(message):
    print('{} {}'.format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), message))

def report(counter, metric_prefix):
    for k, v in counter.iteritems():
        datadog.statsd.gauge('{}.short_lived_containers'.format(metric_prefix), v, tags=["image_name:{}".format(k)])

def determine_names(container):
    label = container.labels.get('com.amazonaws.ecs.container-name')
    if label is not None:
        return [label]
    return set(full_name.split('/')[-1].split(':')[0] for full_name in container.image.tags)

def determine_statsd_host(statsd_host):
    if statsd_host:
        return statsd_host
    return os.environ.get('STATSD_HOST', 'localhost')

def calculate_lifespan(container):
    def normalise(datetimestr):
        ms_removed = datetimestr.split('.')[0]
        z_removed = ms_removed.split('Z')[0]
        return z_removed

    datetime_format = '%Y-%m-%dT%H:%M:%S'
    starttime = datetime.datetime.strptime(normalise(container.attrs['State']['StartedAt']), datetime_format)
    endtime = datetime.datetime.strptime(normalise(container.attrs['State']['FinishedAt']), datetime_format)
    seconds = (endtime - starttime).total_seconds()
    if seconds < 0:
        return None
    return seconds

def poll(interval, short_lived, statsd_host, statsd_port, metric_prefix):
    client = docker.from_env()
    datadog.initialize(statsd_host=statsd_host, statsd_port=statsd_port)
    ignored_statuses = set(['running', 'paused'])

    log('Started container health polling every {} seconds. Will send stats to {}:{}'.format(interval, statsd_host, statsd_port))

    while True:
        containers = client.containers.list(all=True)
        counter = Counter()
        for container in containers:
            if container.status not in ignored_statuses:
                lifespan = calculate_lifespan(container)
                if (lifespan is not None) and (lifespan < short_lived):
                    names = determine_names(container)
                    for name in names:
                        counter[name] += 1
        log('Found short-lived containers: {}'.format(counter))
        report(counter, metric_prefix)

        time.sleep(interval)

def main():
    args = get_args()
    poll(args.interval, args.short_lived, determine_statsd_host(args.statsd_host), args.statsd_port, args.metric_prefix)

if __name__ == '__main__':
    main()
