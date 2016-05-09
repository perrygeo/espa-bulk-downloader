#!/usr/bin/env python
"""
Author: Clay Austin, David Hill
Date: 05/09/2016
Purpose: A simple python client for downloading completed scenes from a users order(s).
Requires: a standard Python install
Version: 2.0
"""

import os
import json
import time
import base64
import random
import shutil
import urllib2
import argparse


class ESPADownloader(object):

    def __init__(self, username, passwd, host):
        self.host = host or "http://espa.cr.usgs.gov"
        self.api_url = self.host + "/api/v0/item-status/{}"
        self.username = username
        self.passwd = passwd

    def get_completed_scenes(self, orderid):
        request = urllib2.Request(self.api_url.format(orderid))
        base64string = base64.b64encode('%s:%s' % (self.username, self.passwd))
        request.add_header("Authorization", "Basic %s" % base64string)
        result = urllib2.urlopen(request)

        download_urls = []

        if result.code == 200:
            data = json.loads(result.read())
            if "msg" in data.keys():
                return data["msg"]
            else:
                scene_list = data['orderid'][orderid]
                for item in scene_list:
                    if item['status'] == 'complete':
                        download_urls.append(item['product_dload_url'])
                return download_urls
        elif result.code == 403:
            return "User authentication failed"
        else:
            return "sorry, there was an issue accessing your data." \
                   "please try again later"


class LocalStorage(object):

    def __init__(self, basedir, orderid):
        self.basedir = basedir
        self.orderid = orderid

    def directory_path(self):
        return ''.join([self.basedir, os.sep, self.orderid, os.sep])

    def scene_path(self, scene_tar):
        return ''.join([self.directory_path(), scene_tar])

    def tmp_scene_path(self, scene_tar):
        return ''.join([self.directory_path(), scene_tar, '.part'])

    def is_stored(self, scene_tar):
        # <tarname>.tar.gz
        return os.path.exists(self.scene_path(scene_tar))

    def file_name(self, scene_tar):
        # 'http://espa-dev.cr.usgs.gov/orders/<order>/<tarname>.tar.gz'
        _slist = scene_tar.split("/")
        _slist.reverse()
        return _slist[0]

    def store(self, scene_url):

        scene_file = self.file_name(scene_url)

        if self.is_stored(scene_file):
            if verbose is not False:
                print scene_file, "already downloaded, skipping.."
            return

        download_directory = self.directory_path()

        #make sure we have a target to land the scenes
        if not os.path.exists(download_directory):
            os.makedirs(download_directory)
            print ("Created target_directory:%s" % download_directory)

        req = urllib2.Request(scene_url)
        req.get_method = lambda: 'HEAD'

        head = urllib2.urlopen(req)
        file_size = int(head.headers['Content-Length'])

        if os.path.exists(self.tmp_scene_path(scene_file)):
            first_byte = os.path.getsize(self.tmp_scene_path(scene_file))
        else:
            first_byte = 0

        print ("Downloading %s to %s" % (scene_file, download_directory))

        while first_byte < file_size:
            first_byte = self._download(first_byte, scene_url)
            time.sleep(random.randint(5, 30))

        os.rename(self.tmp_scene_path(scene_file), self.scene_path(scene_file))

    def _download(self, first_byte, scene_url):
        req = urllib2.Request(scene_url)
        req.headers['Range'] = 'bytes={}-'.format(first_byte)
        scene_file = self.file_name(scene_url)

        with open(self.tmp_scene_path(scene_file), 'ab') as target:
            source = urllib2.urlopen(req)
            shutil.copyfileobj(source, target)

        return os.path.getsize(self.tmp_scene_path(scene_file))


if __name__ == '__main__':
    e_parts = ['ESPA Bulk Download Client Version 1.0.0. [Tested with Python 2.7]\n']
    e_parts.append('Retrieves all completed scenes for the user/order\n')
    e_parts.append('and places them into the target directory.\n')
    e_parts.append('Scenes are organized by order.\n\n')
    e_parts.append('It is safe to cancel and restart the client, as it will\n')
    e_parts.append('only download scenes one time (per directory)\n')
    e_parts.append(' \n')
    e_parts.append('*** Important ***\n')
    e_parts.append('If you intend to automate execution of this script,\n')
    e_parts.append('please take care to ensure only 1 instance runs at a time.\n')
    e_parts.append('Also please do not schedule execution more frequently than\n')
    e_parts.append('once per hour.\n')
    e_parts.append(' \n')
    e_parts.append('------------\n')
    e_parts.append('Examples:\n')
    e_parts.append('------------\n')
    e_parts.append('Linux/Mac: ./download_espa_order.py -u yourusername -p yourpassword -o ALL -d /some/directory/with/free/space\n\n')
    e_parts.append('Windows:   C:\python27\python download_espa_order.py -u yourusername -p yourpassword -o ALL -d C:\some\directory\with\\free\space')
    e_parts.append('\n ')
    epilog = ''.join(e_parts)

    parser = argparse.ArgumentParser(epilog=epilog, formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument("-o", "--order",
                        required=True,
                        help="which order to download (use ALL for every order)")

    parser.add_argument("-d", "--target_directory",
                        required=True,
                        help="where to store the downloaded scenes")

    parser.add_argument("-u", "--username",
                        required=True,
                        help="EE/ESPA account username")

    parser.add_argument("-p", "--password",
                        required=True,
                        help="EE/ESPA account password")

    parser.add_argument("-v", "--verbose",
                        required=False,
                        help="be vocal about process")

    parser.add_argument("-i", "--host",
                        required=False)

    args = parser.parse_args()

    storage = LocalStorage(args.target_directory, args.order)

    print 'Retrieving Products'
    scenes = ESPADownloader(args.username, args.password, args.host).get_completed_scenes(args.order)
    verbose = args.verbose or False
    if isinstance(scenes, str):
        print scenes
    else:
        for scene in scenes:
            storage.store(scene)
