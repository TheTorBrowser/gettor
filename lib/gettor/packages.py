#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
 packages.py: Package related stuff

 Copyright (c) 2008, Jacob Appelbaum <jacob@appelbaum.net>, 
                     Christian Fromme <kaner@strace.org>

 This is Free Software. See LICENSE for license information.

 This module handles all package related functionality
'''

import os
import zipfile
import subprocess
import gettor.gtlog
import gettor.config
import gettor.utils
import re

__all__ = ["Packages"]

log = gettor.gtlog.getLogger()

class Packages:
    #                "bundle name": ("single file regex", "split file regex")
    packageRegex = { "windows-bundle": ("vidalia-bundle-.*.exe$", "vidalia-bundle-.*_split"),
                     "panther-bundle": ("vidalia-bundle-.*-ppc.dmg$", "vidalia-bundle-.*-ppc_split"),
                     "macosx-universal-bundle": ("vidalia-bundle-.*-universal.dmg$", "vidalia-bundle-.*-universal_split"),
                     "source-bundle": ("tor-.*.tar.gz$", "Now to something completely different"),
                     "tor-browser-bundle": ("tor-browser-.*_en-US.exe$", "tor-browser-.*_en-US_split"),
                     "tor-im-browser-bundle": ("tor-im-browser-.*_en-US.exe$", "tor-im-browser-.*_en-US_split"),
                     # Mike won't sign Torbutton; He doesn't get gettor support
                     #"torbutton": "torbutton-current.xpi$",
                   }

    def __init__(self, config):
        self.packageList = {}
        self.distDir = config.getDistDir()
        try:
            entry = os.stat(self.distDir)
        except OSError, e:
            if not gettor.utils.createDir(self.distDir):
                log.error("Bad dist dir %s: %s" % (self.distDir, e))
                raise IOError
        self.packDir = config.getPackDir()
        try:
            entry = os.stat(self.packDir)
        except OSError, e:
            if not gettor.utils.createDir(self.packDir):
                log.error("Bad pack dir %s: %s" % (self.packDir, e))
                raise IOError

    def getPackageList(self):
        # Build dict like 'name': 'name.z'
        try:
            for filename in os.listdir(self.packDir):
                self.packageList[filename[:-2]] = self.packDir + "/" + filename
        except OSError, (strerror):
            log.error("Failed to build package list: %s" % strerror)
            return None

        # Check sanity
        for key, val in self.packageList.items():
            # Remove invalid packages
            if not os.access(val, os.R_OK):
                log.info("Warning: %s not accessable. Removing from list." \
                            % val)
                del self.packageList[key]
        return self.packageList

    def buildPackages(self):
        for filename in os.listdir(self.distDir):
            for (pack, (regex_single, regex_split)) in self.packageRegex.items():
                # Splitfile hacks. XXX: Refactor
                if re.compile(regex_split).match(filename):
                    packSplitDir = None
                    try:
                        packSplitDir = self.packDir + "/" + pack + ".split"
                        if not os.access(packSplitDir, os.R_OK):
                            os.mkdir(packSplitDir)
                    except OSError, e:
                        log.error("Could not create dir %s: %s" \
                                        % (packSplitDir, e))
                    # Loop through split dir, look if every partXX.ZZZ has a 
                    # matching signature, pack them together in a .z
                    splitdir = self.distDir + "/" + filename
                    for splitfile in os.listdir(splitdir):
                        # Skip signature files
                        if splitfile.endswith(".asc"):
                            continue
                        if re.compile(".*split.part.*").match(splitfile):
                            ascfile = splitdir + "/" + splitfile + ".asc"
                            file = splitdir + "/" + splitfile
                            zipFileName = packSplitDir + "/" + splitfile + ".z"
                            if os.access(ascfile, os.R_OK) and os.access(file, os.R_OK):
                                print "ok: ", zipFileName
                                zip = zipfile.ZipFile(zipFileName, "w")
                                zip.write(splitdir + "/" + splitfile, os.path.basename(file))
                                zip.write(ascfile, os.path.basename(ascfile))
                                zip.close()
                            else:
                                log.error("Uhm, expected signature file for %s to be: %s" % (file, ascfile))
                                return False
                if re.compile(regex_single).match(filename):
                    file = self.distDir + "/" + filename
                    ascfile = file + ".asc"
                    zipFileName  = self.packDir + "/" + pack + ".z"
                    # If .asc file is there, build Zip file
                    if os.access(ascfile, os.R_OK):
                        zip = zipfile.ZipFile(zipFileName, "w")
                        zip.write(file, os.path.basename(file))
                        zip.write(ascfile, os.path.basename(ascfile))
                        zip.close()
                        self.packageList[pack] = zipFileName
                        break
        if len(self.packageList) > 0:
            return True
        else:
            log.error("Failed to build packages")
            return False

    def syncWithMirror(self, mirror, silent):
        rsync = ["rsync"]
        rsync.append("-a")
        # Don't download dotdirs
        rsync.append("--exclude='.*'")
        if not silent:
            rsync.append("--progress")
        rsync.append("rsync://%s/tor/dist/current/" % mirror)
        rsync.append(self.distDir)
        process = subprocess.Popen(rsync)
        process.wait()
        return process.returncode

    def getCommandToStr(self, mirror, silent):
        """This is useful for cronjob installations
        """
        rsync = ["rsync"]
        rsync.append("-a")
        # Don't download dotdirs
        rsync.append("--exclude='.*'")
        if not silent:
            rsync.append("--progress")
        rsync.append("rsync://%s/tor/dist/current/" % mirror)
        rsync.append(self.distDir)
        return ''.join(self.rsync)

if __name__ == "__main__" :
    c = gettor_config.Config()
    p = gettorPackages("rsync.torproject.org", c)
    print "Building packagelist.."
    if p.syncwithMirror() != 0:
        print "Failed."
        exit(1)
    if not p.buildPackageList():
        print "Failed."
        exit(1)
    print "Done."
    for (pack, file) in p.getPackageList().items():
        print "Bundle is mapped to file: ", pack, file
