# -*- coding: utf-8 -*-
#
# Copyright (C) 2014, 2015, 2016 Carlos Jenkins <carlos@jenkins.co.cr>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import logging
from sys import stderr, stdout, hexversion
logging.basicConfig(stream=stdout, level=logging.INFO)
#logging.setLevel(logging.INFO)

import hmac
from hashlib import sha1
from hashlib import sha256

from json import loads, dumps
from subprocess import Popen, PIPE
from tempfile import mkstemp
from os import access, X_OK, remove, fdopen
from os.path import isfile, abspath, normpath, dirname, join, basename

import requests
from ipaddress import ip_address, ip_network
from flask import Flask, request, abort


application = Flask(__name__)


@application.route('/', methods=['GET', 'POST'])
def index():
    """
    Main WSGI application entry.
    """

    path = normpath(abspath(dirname(__file__)))

    # Only POST is implemented
    if request.method != 'POST':
        abort(501)

    # Load config
    with open(join(path, 'config.json'), 'r') as cfg:
        config = loads(cfg.read())

    hooks = config.get('hooks_path', join(path, 'hooks'))

    # Allow Github IPs only
    if config.get('github_ips_only', True):
        src_ip = ip_address(
            u'{}'.format(request.access_route[0])  # Fix stupid ipaddress issue
        )
        whitelist = requests.get('https://api.github.com/meta').json()['hooks']
        # If additional_allowed_ips is set add it to whitelist, e.g. for self-hosted Git servers
        additional_allowed_ips = config.get('additional_allowed_ips', [])
        whitelist = whitelist + additional_allowed_ips
        logging.info(whitelist)
        logging.info(src_ip)

        for valid_ip in whitelist:
            if src_ip in ip_network(valid_ip):
                logging.info("IP {ip} is in the network {ip_network}".format(ip=src_ip, ip_network=ip_network(valid_ip)))
                break
            else:
                logging.info("IP {ip} is not in the network{ip_network}".format(ip=src_ip, ip_network=ip_network(valid_ip)))
        else:
            logging.error('IP {} not allowed'.format(src_i))
            abort(403)

    # Enforce secret
    secret = config.get('enforce_secret', '')
    if secret:
        logging.info("Checking secret:" + secret)
        # Only SHA1 is supported
        header_signature = request.headers.get('X-Hub-Signature')

        if header_signature is None:
            logging.info("Github header is not found")
            header_signature = request.headers.get('X-Gogs-Signature')
            header_signature="sha256=" + header_signature
            digest = sha256
        else:
            digest = sha1

        logging.info("Header Signature: " + header_signature)

        if header_signature is None:
            logging.info("Header with Signature is not found")
            abort(403)

        logging.info("Digest is: " + str(digest))
        sha_name, signature = header_signature.split('=')
        logging.debug("SHA name: " + sha_name)
        logging.debug("Signature: " + signature)
        # HMAC requires the key to be bytes, but data is string
        mac = hmac.new(str(secret), msg=request.data, digestmod=digest)
        logging.info("HMAC: " + str(mac))

        # Python prior to 2.7.7 does not have hmac.compare_digest
        if hexversion >= 0x020707F0:
            if not hmac.compare_digest(str(mac.hexdigest()), str(signature)):
                logging.info("hmac.compare_digest error")
                abort(403)
        else:
            # What compare_digest provides is protection against timing
            # attacks; we can live without this protection for a web-based
            # application
            if not str(mac.hexdigest()) == str(signature):
                abort(403)

    # Implement ping
    event = request.headers.get('X-GitHub-Event', 'ping')
    if event == 'ping':
        return dumps({'msg': 'pong'})

    # Gather data
    try:
        payload = request.get_json()
        logging.info(payload)
    except Exception:
        logging.warning('Request parsing failed')
        abort(400)

    # Determining the branch is tricky, as it only appears for certain event
    # types an at different levels
    branch = None
    try:
        # Case 1: a ref_type indicates the type of ref.
        # This true for create and delete events.
        if 'ref_type' in payload:
            if payload['ref_type'] == 'branch':
                branch = payload['ref']

        # Case 2: a pull_request object is involved. This is pull_request and
        # pull_request_review_comment events.
        elif 'pull_request' in payload:
            # This is the TARGET branch for the pull-request, not the source
            # branch
            branch = payload['pull_request']['base']['ref']

        elif event in ['push']:
            # Push events provide a full Git ref in 'ref' and not a 'ref_type'.
            branch = payload['ref'].split('/', 2)[2]

    except KeyError:
        # If the payload structure isn't what we expect, we'll live without
        # the branch name
        pass

    # All current events have a repository, but some legacy events do not,
    # so let's be safe
    name = payload['repository']['name'] if 'repository' in payload else None

    meta = {
        'name': name,
        'branch': branch,
        'event': event
    }
    logging.info('Metadata:\n{}'.format(dumps(meta)))

    # Skip push-delete
    if event == 'push' and payload.get('deleted', False):
        logging.info('Skipping push-delete event for {}'.format(dumps(meta)))
        return dumps({'status': 'skipped'})

    # Possible hooks
    scripts = []
    if branch and name:
        scripts.append(join(hooks, '{event}-{name}-{branch}'.format(**meta)))
    if name:
        scripts.append(join(hooks, '{event}-{name}'.format(**meta)))
    scripts.append(join(hooks, '{event}'.format(**meta)))
    scripts.append(join(hooks, 'all'))

    logging.info("Scripts: " + str(scripts))
    # Check permissions
    #scripts = [s for s in scripts if isfile(s) and access(s, X_OK)]


    existing_script_files = []
    for s in scripts:
        logging.info("Checkung " + s)
        if isfile(s):
            logging.info("Script:" + s + ": isfile()")
            if access(s, X_OK):
                logging.info("Script: " + s + " Access is X_OK")
                existing_script_files.append(s)

    logging.info("Existing Scripts: " + str(existing_script_files))
    if not scripts:
        return dumps({'status': 'nop'})

    # Save payload to temporal file
    osfd, tmpfile = mkstemp()
    with fdopen(osfd, 'w') as pf:
        pf.write(dumps(payload))

    # Run scripts
    ran = {}
    for s in existing_script_files:
        logging.info("Executing " + s)
        proc = Popen(
            [s, tmpfile, event],
            stdout=PIPE, stderr=PIPE
        )
        stdout, stderr = proc.communicate()

        ran[basename(s)] = {
            'returncode': proc.returncode,
            'stdout': stdout.decode('utf-8'),
            'stderr': stderr.decode('utf-8'),
        }

        logging.info(stdout)
        logging.info(stderr)

        # Log errors if a hook failed
        if proc.returncode != 0:
            logging.error('{} : {} \n{}'.format(
                s, proc.returncode, stderr
            ))

    # Remove temporal file
    remove(tmpfile)

    info = config.get('return_scripts_info', False)
    if not info:
        return dumps({'status': 'done'})

    output = dumps(ran, sort_keys=True, indent=4)
    logging.info(output)
    return output


if __name__ == '__main__':
    application.run(debug=True, host='0.0.0.0', port='25002')
