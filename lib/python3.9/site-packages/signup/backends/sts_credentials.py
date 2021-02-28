# Copyright (c) 2020, Djaodjin Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import datetime, base64, hashlib, hmac, json, logging

import boto3

from .. import settings
from ..compat import is_authenticated, urlparse
from ..helpers import datetime_or_now


LOGGER = logging.getLogger(__name__)


def temporary_security_token(request,
                             aws_upload_role=None, aws_external_id=None,
                             aws_region=None, at_time=None):
    """
    Create temporary security credentials on AWS. This typically needed
    to allow uploads from the browser directly to S3.
    """
    if not is_authenticated(request):
        return
    at_time = datetime_or_now(at_time)

    if ('access_key_expires_at' in request.session
        and at_time + datetime.timedelta(seconds=5) < datetime_or_now(
                request.session['access_key_expires_at'])):
        # +5s buffer, in case of clock drift.
        return

    # Lazy creation of temporary credentials.
    if not aws_upload_role:
        aws_upload_role = settings.AWS_UPLOAD_ROLE
    if not aws_external_id:
        aws_external_id = settings.AWS_EXTERNAL_ID
    kwargs = {}
    if aws_external_id:
        kwargs = {"ExternalId": aws_external_id}
    if not aws_region:
        aws_region = settings.AWS_REGION
    conn = boto3.client('sts', region_name=aws_region)
    # AWS will fail if we don't sanetize and limit the length
    # of the session key.
    aws_session_key = request.session.session_key.replace('/', '')[:64]
    if aws_session_key != request.session.session_key:
        LOGGER.warning("sanetized session key %s to %s for %s in order to"\
            " match AWS requirements", request.session.session_key,
            aws_session_key, request.user, extra={'request': request})
    # See http://boto.cloudhackers.com/en/latest/ref/sts.html#\
    # boto.sts.STSConnection.assume_role
    duration_seconds = 3600
    access_key_expires_at = at_time + datetime.timedelta(
        seconds=duration_seconds)
    assumed_role = conn.assume_role(RoleArn=aws_upload_role,
        RoleSessionName=aws_session_key, **kwargs)
    request.session['access_key'] = assumed_role['Credentials']['AccessKeyId']
    request.session['secret_key'] \
        = assumed_role['Credentials']['SecretAccessKey']
    request.session['security_token'] \
        = assumed_role['Credentials']['SessionToken']
    request.session['access_key_expires_at'] = access_key_expires_at.isoformat()
    LOGGER.info('AWS temporary credentials for %s to assume role %s: %s',
        request.user, aws_upload_role, request.session['access_key'],
        extra={'event': 'create-aws-credentials',
            'request': request, 'aws_role': aws_upload_role,
            'aws_access_key': request.session['access_key']})
    LOGGER.debug('AWS Access Key %s, Secret Key=%s, Security Token=%s',
        request.session['access_key'], request.session['secret_key'],
        request.session['security_token'])


def _signed_policy(region, service, requested_at,
                   access_key, secret_key, security_token,
                   bucket=None, key_prefix="", acl=None):
    #pylint:disable=too-many-arguments,too-many-locals
    signature_date = requested_at.strftime("%Y%m%d")
    x_amz_credential = '/'.join([
        access_key, signature_date, region, service, 'aws4_request'])
    x_amz_date = '%sT000000Z' % signature_date
    conditions = [
        {"bucket": bucket},
        {"x-amz-algorithm": "AWS4-HMAC-SHA256"},
        {"x-amz-credential": x_amz_credential},
        {"x-amz-date": x_amz_date},
        {"x-amz-security-token": security_token},
        ["starts-with", "$key", key_prefix],
        ["starts-with", "$Content-Type", ""]
    ]
    if acl is not None:
        conditions += [{"acl": acl}]
    if acl is None or acl != 'public-read':
        conditions += [{"x-amz-server-side-encryption": "AES256"}]
    policy = json.dumps({
        "expiration": (requested_at + datetime.timedelta(
            hours=24)).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        "conditions": conditions}).encode("utf-8")
    policy_base64 = base64.b64encode(policy).decode(
        "utf-8").replace('\n', '')
    date_key = hmac.new(("AWS4%s" % secret_key).encode("utf-8"),
        signature_date.encode("utf-8"),
        hashlib.sha256).digest()
    date_region_key = hmac.new(
        date_key, region.encode("utf-8"),
        hashlib.sha256).digest()
    date_region_service_key = hmac.new(
        date_region_key, service.encode("utf-8"),
        hashlib.sha256).digest()
    signing_key = hmac.new(
        date_region_service_key, "aws4_request".encode("utf-8"),
        hashlib.sha256).digest()
    policy_signature = hmac.new(
        signing_key, policy_base64.encode("utf-8"),
        hashlib.sha256).hexdigest()
    if acl is not None:
        acl_prefix = acl.replace('-', '_') + "_"
        context = {'acl': acl}
    else:
        acl_prefix = ""
        context = {}
    context.update({
        'access_key': access_key,
        'security_token': security_token,
        "%saws_policy" % acl_prefix: policy_base64,
        "%saws_policy_signature" % acl_prefix: policy_signature,
        'x_amz_credential': x_amz_credential,
        'x_amz_date': x_amz_date})
    return context


def aws_bucket_context(request, location, acls=None, aws_upload_role=None,
                       aws_external_id=None, aws_region=None):
    """
    Context to use in templates to upload from the client brower
    to the bucket directly.
    """
    #pylint:disable=too-many-arguments
    context = {}
    if is_authenticated(request):
        # Derives a bucket_name and key_prefix from a location
        # (ex: s3://bucket_name/key_prefix,
        # https://s3-region.amazonaws/bucket_name/key_prefix)
        parts = urlparse(location)
        bucket_name = parts.netloc.split('.')[0]
        key_prefix = parts.path
        if bucket_name.startswith('s3-'):
            aws_region = bucket_name[3:]
            name_parts = key_prefix.split('/')
            if name_parts and not name_parts[0]:
                name_parts.pop(0)
            bucket_name = name_parts[0]
            key_prefix = '/'.join(name_parts[1:])
        if key_prefix.startswith('/'):
            # we rename leading '/' otherwise S3 copy triggers a 404
            # because it creates an URL with '//'.
            key_prefix = key_prefix[1:]
        if key_prefix and key_prefix.endswith('/'):
            key_prefix = key_prefix[:-1]
        if not aws_region:
            aws_region = settings.AWS_REGION

        requested_at = datetime_or_now()

        # Lazy creation of temporary credentials.
        temporary_security_token(request, aws_upload_role=aws_upload_role,
            aws_external_id=aws_external_id, aws_region=aws_region,
            at_time=requested_at)

        if acls is not None:
            for acl in acls:
                context.update(_signed_policy(
                    aws_region, "s3", requested_at,
                    request.session['access_key'],
                    request.session['secret_key'],
                    security_token=request.session['security_token'],
                    bucket=bucket_name, key_prefix=key_prefix, acl=acl))
        else:
            context.update(_signed_policy(
                aws_region, "s3", requested_at,
                request.session['access_key'],
                request.session['secret_key'],
                security_token=request.session['security_token'],
                bucket=bucket_name, key_prefix=key_prefix))
        context.update({"location": "https://%s.s3-%s.amazonaws.com/%s" % (
                bucket_name, aws_region, key_prefix)})
    return context


class AWSContextMixin(object):

    def get_context_data(self, *args, **kwargs):
        #pylint: disable=unused-argument
        return aws_bucket_context(self.request, kwargs.get('location', None),
            acls=kwargs.get('acls', None),
            aws_upload_role=kwargs.get('aws_upload_role', None),
            aws_external_id=kwargs.get('aws_external_id', None),
            aws_region=kwargs.get('aws_region', None))
