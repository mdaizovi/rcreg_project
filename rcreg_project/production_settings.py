import os
from settings import *

#advice from : http://stackoverflow.com/questions/88259/how-do-you-configure-django-for-simple-development-and-deployment
DEBUG = False
TEMPLATE_DEBUG = DEBUG

#This is the pythonanywhere DB. swap before deployment.
DATABASES = {
   'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'rcregsite$default',
        'USER': 'rcregsite',
        'PASSWORD': 'mice4rice',
        'HOST': 'mysql.server',
        #https://groups.google.com/forum/#!topic/sahana-eden/wjGdwEdZK6Q
        #'HOST': 'rcregsite.mysql.pythonanywhere-services.com',
        #'PORT': '', #blank so default is selected
        }
}
