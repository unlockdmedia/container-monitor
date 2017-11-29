#!/usr/bin/env python
#
# Monitor container health

from __future__ import print_function
import argparse
import time
import datetime
from collections import Counter
import docker

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--interval', default=60, help='Number of seconds between each poll')
    parser.add_argument('--short-lived', dest='short_lived', default=300, help='Number of lifespan seconds to be consider short-lived containers')
    return parser.parse_args()

def log(message):
    print('{} {}'.format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), message))

def determine_name(full_name):
    domain_removed = full_name.split('/')[-1]
    tag_removed = domain_removed.split(':')[0]
    return tag_removed

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

def poll(interval, short_lived):
    client = docker.from_env()

    ignored_statuses = set(['running', 'paused'])

    while True:
        containers = client.containers.list(all=True)
        counter = Counter()
        for container in containers:
            if container.status not in ignored_statuses:
                lifespan = calculate_lifespan(container)
                if (lifespan is not None) and (lifespan < short_lived):
                    names = set(determine_name(full_name) for full_name in container.image.tags)
                    for name in names:
                        counter[name] += 1
        log('Found short-lived containers: {}'.format(counter))

        time.sleep(interval)

def main():
    args = get_args()
    poll(args.interval, args.short_lived)

if __name__ == '__main__':
    main()
