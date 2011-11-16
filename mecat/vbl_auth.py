# -*- coding: utf-8 -*-
#
# Copyright (c) 2010-2011, Monash e-Research Centre
#   (Monash University, Australia)
# Copyright (c) 2010-2011, VeRSI Consortium
#   (Victorian eResearch Strategic Initiative, Australia)
# All rights reserved.
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#    *  Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#    *  Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#    *  Neither the name of the VeRSI, the VeRSI Consortium members, nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE REGENTS AND CONTRIBUTORS ``AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE REGENTS AND CONTRIBUTORS BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
'''
Created on 20/06/2011

.. moduleauthor:: Ulrich Felzmann <ulrich.felzmann@versi.edu.au>
'''

import logging
from string import lower
from suds.client import Client
import json

from django.conf import settings

from tardis.tardis_portal.auth.interfaces import AuthProvider, GroupProvider


logger = logging.getLogger('tardis.mecat')


EPN_LIST = "_epn_list"

auth_key = u'vbl'
auth_display_name = u'VBL'


class VblGroupProvider(GroupProvider):
    name = u'vbl_group'

    def getGroups(self, request):
        """
        Return an iteration of the available EPNs for a user from the
        VBL. This determines which experiments a authenticated user is
        allowed to see. The VBL SOAP webservice returns a string with
        EPNs, separated by commas (',') which is also stored in the
        session variable.

        """

        # the user needs to be authenticated
        if not request.user.is_authenticated():
            return []

        # check if the user is linked to any experiments
        if not EPN_LIST in request.session:
            return []

        # the epns should be stored in the session if the user
        # authenticated against the vbl backend below
        else:
            return request.session[EPN_LIST]


    def searchGroups(self, **filter):

        epn = filter.get('name')
        if not epn:
            return []

        # we can't really search for groups yet 
        # TODO: implement user's lookup through SOAP call
        # requires somethings like the following
        # users = str(self.client.service.VBLgetEmailsFromExpID(epn))

        # chop off literals (a,b,c) from epn (2467a -> 2467)
        from re import match
        epn = match('\d*', epn).group(0)

        try:
            id = int(epn)
        except ValueError:
            id = 0

        return [{'id': id,
                 'display': 'VBL/EPN_%s' % epn,
                 #'members': users.split(',')}]
                 'members': []}]


class Backend(AuthProvider):
    def _get_client(self):
        try:
            VBLTARDISINTERFACE = settings.VBLTARDISINTERFACE
        except AttributeError:
            logger.error('setting VBLTARDISINTERFACE not configured')
            return None

        try:
            proxy = getattr(settings, 'VBLPROXY', None)
            # Switch the suds cache off, otherwise suds will try to
            # create a tmp directory in /tmp. If it already exists but
            # has the wrong permissions, the authentication will fail.
            return Client(VBLTARDISINTERFACE, cache=None, proxy=proxy)
        except:
            logger.exception('')
            return None


    """
    Authenticate against the VBL SOAP Webservice. It is assumed that
    the request object contains the username and password to be
    provided to the VBLauthenticate function.
    """
    def authenticate(self, request):
        username = lower(request.POST['username'])
        password = request.POST['password']

        if not username or not password:
            return None

        client = self._get_client()

        # authenticate user and update group memberships
        result = str(client.service.VBLauthenticate(username, password))
        user_info = self._load_user_info(result)
        if not user_info:
            logger.warning('VBLauthenticate failure: %s %s' % (username, result))
            return None

        request.session[EPN_LIST] = user_info['epns']

        logger.info('VBL user %s groups %s' % (username, str(request.session[EPN_LIST])))
        return user_info


    def get_user(self, user_id):
        if not user_id:
            return None

        client = self._get_client()
        result = str(client.service.VBLgetUserInfo(user_id))
        user_info = self._load_user_info(result)
        if not user_info:
            logger.info('VBLgetUserInfo user not found: %s %s' % (user_id, result))
        return user_info


    def _load_user_info(self, json_user_info):
        try:
            user_info = json.loads(json_user_info)
            return self._make_user_dict(user_info)
        except:
            return None


    def _make_user_dict(self, user_info):
        return { 'display': user_info['name'],
                 'id': user_info['username'],
                 'email': user_info.get('email', ''),
                 'first_name': user_info['first_name'],
                 'last_name': user_info['last_name'],
                 'epns': user_info['epns'],
               }

