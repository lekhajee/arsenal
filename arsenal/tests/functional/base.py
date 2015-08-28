# Copyright 2015 Rackspace
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import requests
import subprocess
import ConfigParser
import math
from random import randint

from oslotest import base


class TestCase(base.BaseTestCase):
    """
    Base test class for all functional tests
    """

    def generate_config_file_name(self, name='test'):
        """
        Create a config file name appending the port to it
        """
        return name + str(self.port) + '.conf'

    def setUp(self):
        """
        Set the endpoints for ironic and glance.
        Create a config file for arsenal with default values
        set in the `set_config_values` method.
        """
        super(TestCase, self).setUp()
        self.processes_to_kill = []
        self.flavors = 3
        self.port = str(randint(2000, 9000))
        self.mimic_ironic_url = "http://localhost:{0}/ironic/v1/nodes/detail".format(self.port)
        self.mimic_glance_url = "http://localhost:{0}/glance/v2/images".format(self.port)
        self.default_config_file = 'test_default' + self.port + '.conf'
        config_values = self.set_config_values()
        self.create_arsenal_config_file(config_values,
                                        file_name=self.default_config_file)

    def tearDown(self):
        """
        Kill arsenal and mimic processes
        """
        super(TestCase, self).tearDown()

        for each in self.processes_to_kill:
            try:
                each.kill()
            except OSError as e:
                if not ('No such process' in str(e)):
                    raise

    def start_mimic_service(self):
        """
        Start the mimic service and wait for the service to be started.
        """
        p = subprocess.Popen(['twistd', '-n', '--pidfile=twistd{}.pid'.format(self.port),
                              'mimic', '-l', self.port],
                             stdout=subprocess.PIPE)
        self.processes_to_kill.append(p)
        while True:
            line = p.stdout.readline()
            if ((line == '' and p.poll() is not None) or  # process done
                    "Starting factory <twisted.web.server.Site instance" in line):
                break

    def start_arsenal_service(self, config_file='arsenal.conf',
                              service_status="Started Arsenal service"):
        """
        Start the arsenal service with the given config file
        TO DO: Check for the 'service started' message in the logs
        """
        a = subprocess.Popen(['arsenal-director', '--config-file', config_file,
                              '-v'],
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        self.processes_to_kill.append(a)
        while True:
            line = a.stdout.readline()
            if ((line == '' and a.poll() is not None) or  # process done
                    service_status in line):
                break

    def calculate_percentage_to_be_cached(self, total_nodes, percentage):
        """
        Calulates the nodes to be cached given the percentage and the
        total_nodes.
        """
        return (math.floor((total_nodes / 3) * percentage) * 3)

    def set_config_values(self, mimic_endpoint='http://localhost',
                          dry_run=False, interval=1, rate_limit=100,
                          percentage_to_cache=0.5, image_weights=None):
        """
        Set values for the arsenal config file.
        """
        port = self.port
        image_weights = image_weights or {'OnMetal - CentOS 6': 80,
                                          'OnMetal - CentOS 7': 80,
                                          'OnMetal - CoreOS (Alpha)': 11,
                                          'OnMetal - CoreOS (Beta)': 1,
                                          'OnMetal - CoreOS (Stable)': 5,
                                          'OnMetal - Debian 7 (Wheezy)': 60,
                                          'OnMetal - Debian 8 (Jessie)': 14,
                                          'OnMetal - Debian Testing (Stretch)': 2,
                                          'OnMetal - Debian Unstable (Sid)': 2,
                                          'OnMetal - Fedora 21': 1,
                                          'OnMetal - Fedora 22': 2,
                                          'OnMetal - Ubuntu 12.04 LTS (Precise Pangolin)': 132,
                                          'OnMetal - Ubuntu 14.04 LTS (Trusty Tahr)': 163,
                                          'OnMetal - Ubuntu 15.04 (Vivid Vervet)': 3}
        return {
            'director':
                {'scout': 'onmetal_scout.OnMetalScout',
                 'dry_run': dry_run,
                 'poll_spacing': interval,
                 'directive_spacing': interval,
                 'cache_directive_rate_limit': rate_limit,
                 'cache_directive_limiting_period': interval,
                 'eject_directive_rate_limit': rate_limit,
                 'eject_directive_limiting_period': interval,
                 'log_statistics': True},
            'client_wrapper':
                {'call_max_retries': 3,
                 'call_retry_interval': 3,
                 'os_tenant_name': 232323,
                 'os_username': 'test-user',
                 'region_name': 'ORD',
                 'service_name': 'cloudServersOpenStack',
                 'auth_system': 'rackspace',
                 'os_api_url': '{0}:{1}/identity/v2.0'.format(mimic_endpoint, port),
                 'os_password': 'test-password'},
            'nova': {},
            'ironic':
                {'admin_username': 'test-admin',
                 'admin_password': 'test-admin-password',
                 'admin_tenant_name': 99999,
                 'admin_url': '{0}:{1}/identity/v2.0'.format(mimic_endpoint, port),
                 'api_endpoint': '{0}:{1}/ironic/v1'.format(mimic_endpoint, port)},
            'glance':
                {'api_endpoint': '{0}:{1}/glance/v2'.format(mimic_endpoint, port),
                 'admin_auth_token': 'any-token-works'},
            'simple_proportional_strategy':
                {'percentage_to_cache': percentage_to_cache},
            'strategy':
                {'module_class': 'simple_proportional_strategy.SimpleProportionalStrategy',
                 'image_weights': image_weights}
        }

    def create_arsenal_config_file(self, config_values, file_name='test.conf'):
        """
        Given `config_values` object set the values in the arsensal.conf file.
        """
        config = ConfigParser.RawConfigParser()
        for each_key in config_values.keys():
            if not config.has_section(each_key):
                config.add_section(each_key)
            for key, value in config_values[each_key].iteritems():
                config.set(each_key, key, value)
        f = open(file_name, 'w')
        config.write(f)
        f.close()

    def get_ironic_nodes(self, provisioned=False):
        """
        Get the list of ironic nodes with details.
        Set `provisioned` to True to return all the ironic nodes
        including the ones already provisioned
        """
        nodes_list_response = requests.get(self.mimic_ironic_url)
        self.assertEqual(nodes_list_response.status_code, 200)
        ironic_nodes_list = nodes_list_response.json()['nodes']
        if provisioned:
            return [each_node for each_node in ironic_nodes_list
                    if each_node.get('instance_uuid')]
        return [each_node for each_node in ironic_nodes_list
                if not each_node.get('instance_uuid')]

    def get_cached_ironic_nodes(self, filter_by_flavor=False):
        """
        Get the cached nodes from the list of nodes in ironic.
        If `filter_by_flavor` is `True` return a map of each flavor to
        cached ironic nodes of that flavor.
        """
        node_list = self.get_ironic_nodes()
        if filter_by_flavor:
            cache_node_by_flavor = {
                'onmetal-compute1': [], 'onmetal-io1': [], 'onmetal-memory1': []}
            for each_node in node_list:
                if (each_node['driver_info'].get('cache_image_id')) and \
                   (each_node['extra'].get('flavor') in cache_node_by_flavor.keys()):
                    cache_node_by_flavor[each_node['extra']['flavor']].append(each_node)
            return cache_node_by_flavor
        return [each_node for each_node in node_list
                if (each_node['driver_info'].get('cache_image_id'))]

    def get_image_id_to_name_map_from_mimic(self):
        """
        Get a list of images and map the image id to name.
        Returns a dict object mapping the image id to image name
        """
        image_list_response = requests.get(self.mimic_glance_url)
        self.assertEqual(image_list_response.status_code, 200)
        return {each["id"]: each["name"] for each in image_list_response.json()['images']}

    def list_ironic_nodes_by_image(self, node_list, count=False):
        """
        Given a list of nodes, map the nodes of the same image and return
        list of nodes per image.
        If `count` is `True` return the count of nodes per image.
        """
        image_map = self.get_image_id_to_name_map_from_mimic()
        nodes_per_image = {}
        for each_node in node_list:
            image_name = image_map.get(each_node['driver_info']['cache_image_id'])
            if nodes_per_image.get(image_name):
                nodes_per_image[image_name].append(each_node['uuid'])
            else:
                nodes_per_image[image_name] = [each_node['uuid']]
        if count:
            nodes_per_image_count = {}
            for key, value in nodes_per_image.iteritems():
                nodes_per_image_count[key] = len(value)
            return nodes_per_image_count
        return nodes_per_image