#!/usr/bin/python3
import os, sys
import locale
import gettext

# Change this variable to your app name!
#  The translation files will be under 
#  @LOCALE_DIR@/@LANGUAGE@/LC_MESSAGES/@APP_NAME@.mo
#
APP_NAME = "pygiftparser"

# For a server side installation 
#
# PREFIX = sys.prefix

# for a local dir
# PREFIX = '/home/tommasi/Enseign/devel/gift'
PREFIX=os.path.abspath(os.path.join(__file__,'..','..'))
APP_DIR = os.path.join (PREFIX,
                        'share')
LOCALE_DIR = os.path.join(APP_DIR, 'locale')

# Now we need to choose the language. We will provide a list, and gettext
# will use the first translation available in the list
#
#  In maemo it is in the LANG environment variable
#  (on desktop is usually LANGUAGES)
#
DEFAULT_LANGUAGES = os.environ.get('LANG', '').split(':')
DEFAULT_LANGUAGES += ['en_US']

# Try to get the languages from the default locale
languages = []
lc, encoding = locale.getdefaultlocale()
if lc:
    languages = [lc]

# Concat all languages (env + default locale), 
#  and here we have the languages and location of the translations
#
languages += DEFAULT_LANGUAGES
mo_location = LOCALE_DIR

# Lets tell those details to gettext
#  (nothing to change here for you)
gettext.install (True)
gettext.bindtextdomain (APP_NAME,
                        mo_location)
gettext.textdomain (APP_NAME)
language = gettext.translation (APP_NAME,
                                mo_location,
                                languages = languages,
                                fallback = True)

# And now in your modules you can do:
#
# import i18n
# _ = i18n.language.gettext
#

