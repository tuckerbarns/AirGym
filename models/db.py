# -*- coding: utf-8 -*-

db = DAL('sqlite://storage.sqlite')
response.generic_patterns = ['*'] if request.is_local else []
from gluon.tools import Auth, prettydate
from gluon.utils import web2py_uuid
auth = Auth(db)

def HField(*a,**b):
    b['writable']=b['readable']=False
    return Field(*a,**b)

auth.settings.extra_fields['auth_user'] = [
    HField('full_name',compute=lambda row: '%(first_name)s %(last_name)s (%(year_of_birth)s)' % row),
    Field('year_of_birth','integer',requires=IS_MATCH('(19|20)\d\d')),
    Field('address'),
    Field('city'),
    Field('zip'),
    Field('state',requires=IS_IN_SET(STATES)),
    Field('country',default='US'),
    Field('phone'),
    Field('twitter'),
    Field('facebook'),
    Field('home_page',requires=IS_EMPTY_OR(IS_URL())),
    Field('sports','list:string',requires=IS_IN_SET(SPORTS,multiple=True)),
    Field('profile_public','boolean',default=True),
    Field('facility_owner','boolean',default=False),
    Field('mugshot','upload',requires=IS_NULL_OR(IS_IMAGE())),
    Field('about_you','text'),
]

auth.define_tables(username=True, signature=False)

## configure email
mail = auth.settings.mailer
mail.settings.server = EMAIL_SERVER
mail.settings.sender = EMAIL_SENDER
mail.settings.login = EMAIL_LOGIN

## configure auth policy
auth.settings.registration_requires_verification = True
auth.settings.registration_requires_approval = False
auth.settings.reset_password_requires_verification = True

from gluon.contrib.login_methods.rpx_account import use_janrain
use_janrain(auth, filename='private/janrain.key')
