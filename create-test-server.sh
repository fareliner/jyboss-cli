#!/bin/env bash

# ******************************************************************
# OS specific support.  $var _must_ be set to either true or false.
cygwin=false
darwin=false
os400=false
hpux=false
case "`uname`" in
CYGWIN*) cygwin=true;;
Darwin*) darwin=true;;
OS400*) os400=true;;
HP-UX*) hpux=true;;
esac

# ******************************************************************
# verbose messaging
function msg()
{
  local _MSG=$1
  shift
  printf "[\e[94mINFO\e[39m] ${_MSG}\n" $* 1>&2
}


# ******************************************************************
# main line

PATH=.:$PATH

if [ -z "${CI_PROJECT_DIR}" ]; then
  export CI_PROJECT_DIR=$(pwd)
fi

# the place where the testing server will be installed
JBOSS_HOME="${CI_PROJECT_DIR}/tmp/server"

# setup maven repo
if [ -z "${M2_REPO}" ]; then
  export M2_REPO=~/.m2/repository
fi


# we can infer coordinates from pom
KEYCLOAK_VERSION=3.4.3.Final

KEYCLOAK_PRODUCT=keycloak
KEYCLOAK_GROUP=org.keycloak
KEYCLOAK_DIST_FORMAT=tar.gz

# RedHat SSO Commercial Distro
#KEYCLOAK_PRODUCT=rh-sso
#KEYCLOAK_GROUP=com.redhat.jboss
#KEYCLOAK_DIST_FORMAT=zip

if [ -d "${JBOSS_HOME}" ]; then
  msg "Remove ${KEYCLOAK_PRODUCT} home"
  rm -rf ${JBOSS_HOME}
fi

mkdir -p ${JBOSS_HOME} 1>&2

msg "Download ${KEYCLOAK_PRODUCT} distribution package"
mvn dependency:get -DgroupId="${KEYCLOAK_GROUP}" \
                   -DartifactId="${KEYCLOAK_PRODUCT}-server-dist" \
                   -Dversion="${KEYCLOAK_VERSION}" \
                   -Dpackaging="${KEYCLOAK_DIST_FORMAT}" 1>&2

msg "Unpack ${KEYCLOAK_PRODUCT}-${KEYCLOAK_VERSION} server"
tar xzf ${M2_REPO}/${KEYCLOAK_GROUP/.//}/${KEYCLOAK_PRODUCT}-server-dist/${KEYCLOAK_VERSION}/${KEYCLOAK_PRODUCT}-server-dist-${KEYCLOAK_VERSION}.${KEYCLOAK_DIST_FORMAT} \
         --strip-components=1 \
         -C ${JBOSS_HOME} 1>&2

msg '------------------------------------------------------------------------'
msg "Configure ${KEYCLOAK_PRODUCT} server"
${JBOSS_HOME}/bin/jboss-cli.sh --file=keycloak-setup.cli 1>&2

msg '------------------------------------------------------------------------'

printf "\n# Set the below variable prior to executing tests\n\n"

if $cygwin; then
  JBOSS_HOME=$(cygpath -aw "${JBOSS_HOME}")
fi

msg 'Server home is %s' "${JBOSS_HOME}"

printf 'export JBOSS_HOME=\"%s\"\n\n' "${JBOSS_HOME}"

