#!/usr/bin/env python
from __future__ import with_statement
from fabric.api import *
from fabric.colors import *
from fabric.contrib.files import exists
import os
__author__ = 'peter'

PROJECT_NAME = 'shikafa'
VERSION = '0.1'
VIRT_DIR = "deb-build"
DEBIAN_PROJECT_DEP = "python,build-essential,python-dev,libmysqlclient-dev," \
                     "libpq-dev,nginx,libxml2-dev,libxslt1-dev,libffi-dev,libjpeg-dev"
INSTALLATION_DIR = "/var/www"
DOCKER_LOG_DIR = "/src/webapp/shinkafa/logs"
SRC_DIR = os.path.dirname(os.path.abspath(__file__))
BUILD_DIR = os.path.join(SRC_DIR, VIRT_DIR)



def remove_old_build():
    with settings(warn_only=True):
        local("rm -r build")
        local("rm -r dist")
        local("rm *.deb")
        local("rm -r SHINKAFA.egg-info")





def package_tar():
    with settings(warn_only=True):
        task_to_run = local("python setup.py sdist")
    if task_to_run.failed:
        abort("Error during packaging of tar file")


def copy_tar_to_docker_folder():
    """
        Task to copy our compressed django tar
        to the docker folder for docker build
    """
    with settings(warn_only=True):
        copy_cmd = local("cp dist/*.tar.gz docker/")
    if copy_cmd.failed:
        abort("Error when copying compressed tar.gz for django app to docker folder\n"
              " Are you sure you executed the  package_tar() task")
    print("Finished copying of compressed tar to docker folder")


def build_docker_image():
    """
        Start the docker build process and specifying a tag
        to the flexisaf/shinkafa.
        The files to build are contain inside the docker
        folder
    """
    docker_build = local('docker build -t flexisaf/shinkafa docker/')
    if docker_build.failed:
        abort("Docker build failed ")
    else:
        print("Docker image build successful")




@task()
def run_test():
    """
        Run all test on the application this task
        can be executed on it own. Also the task is
        executed on a docker instance when code a push to
        develop. so as to maintain QA
    """
    with settings(warn_only=True):
        test_result = local('python runtest.py')
    if test_result.failed:
        abort(red("Test did not pass, you have broken our code or something.. went bad when u wrote your code"))
    if test_result.succeed:
        print green("All test passed *******")



def start_docker_process(docker_host="staging"):
    """
        Start the container with a name shinkafa, so we can use to
        kill the container later, also run the container in a detach
        mode and always restart the docker container if for
        any reason the process inside crashes
    """
    host_machine_pwd = local('echo $HOME')
    host_log_directory = '/home/ubuntu/webapp/log/shinkafa'
    # host_log_directory = os.path.join(host_machine_pwd, 'webapp/log/shinkafa')
    # check if there is a log directory on the host machine
    if not os.path.exists(host_log_directory):
        # then create the log directory
        local("mkdir -p %s" % host_log_directory)
    docker_tag = "flexisaf/shinkafa:latest"
    client_db_name = "shinkafa_" + docker_host
    secret_key = "your_secrete393939_key_here_please"
    docker_env = "-e DB_NAME='%s' -e CLIENT_S3_FOLDER='%s' -e SECRET_KEY='%s'" % (client_db_name, docker_host,secret_key)
    local("docker run %s --name=shinkafa --detach=true --restart=always --publish=80:80 --volume=%s:%s %s"
        % (docker_env, host_log_directory, DOCKER_LOG_DIR, docker_tag))


@task()
def stop_container():
    local("docker stop shinkafa")


@task()
def start_container():
    local("docker start shinkafa")


@task()
def restart_container():
    local("docker restart shinkafa")



@task()
def start_build_pipeline():
    remove_old_build()
    package_tar()
    copy_tar_to_docker_folder()
    build_docker_image()


@task()
def ship_docker():
    """
        Ship the compressed docker image to the host machine
        that will run the container.
        This process basically copy the compressed tar from
        the build ci to the production machine
        and offload the tar ball on the production
        machine which then start the docker process
    """
    with settings(warn_only=True, colorize_error=True):
        # check if this is the first time we are loading this docker on the machine
        docker_restart = local("docker restart shinkafa")
    if docker_restart.failed:
        print(red("Docker process restarted, failed Starting a new process"))
        # only start a new docker process if there is no current process running
        start_docker_process(docker_host="shinkafa")  # start a new docker process