__author__ = 'Rustam Bogubaev'

import argparse
import os
import imghdr
from PIL import Image
from datetime import datetime
import shutil
import re

class ProcessType:
    BY_DATE, BY_SIZE = range(0, 2)
    COPY, MOVE = range(2, 4)

    @classmethod
    def key(clazz, val):
        for k, v in vars(clazz).iteritems():
            if v == val:
                return k

    @classmethod
    def val(clazz, key):
        return getattr(clazz, key.upper(), None)


class OrganizeImages():
    def __init__(self, dirSource, dirDestination):
        self.command = None
        self.organizeBy = None
        self.dirSource = dirSource
        self.dirDestination = dirDestination
        self.minWidth = None
        self.minHeight = None
        self.buildTree = False
        self.useFileTime = False


    def process(self):
        self.processDirectory(self.dirSource)


    def processDirectory(self, directory):
        if not os.path.exists(directory):
            print(directory + " is skipped, doesn't exists")
            return

        for file in os.listdir(directory):
            absolute = os.path.join(directory, file)

            if os.path.islink(absolute):
                print("!!!symlink, skipping: " + absolute)
                continue

            if os.path.isdir(absolute):
                self.processDirectory(absolute)
            else:
                self.processFile(absolute)


    def processFile(self, file):
        if not os.path.exists(file):
            print(file + " is skipped, doesn't exists")
            return

        type = imghdr.what(file)

        if type is None:
            return

        try:
            self.processImage(file, type)
        except IOError as e:
            print("ERROR! Unable to process " + file + " (" + e.message + ")")
            return


    def processImage(self, file, type):
        metadata = ImageMetadata(file, type)
        metadata.parse()

        considerDimensionsLimit = self.considerDimensionsLimit()
        matchesMinimumDimensions = metadata.matchesMinimumDimensions(self.minWidth, self.minHeight)

        if considerDimensionsLimit and matchesMinimumDimensions is not True:
            message = []
            message.append("skipped due to dimensions limit ")
            message.append("(")
            message.append("required=" + str(self.minWidth) + "x" + str(self.minHeight))
            message.append(", ")
            message.append("actual=" + str(metadata.width) + "x" + str(metadata.height))
            message.append(", ")
            message.append(file)
            message.append(")")

            print("".join(message))

            return

        treePath = self.buildTreePath(metadata)

        if metadata.dates.hasMetaDate():
            self.copyImage(file, ProcessType.key(self.organizeBy) + "/EXIF-Y", treePath)
        else:
            self.copyImage(file, ProcessType.key(self.organizeBy) + "/EXIF-N", treePath)


    def copyImage(self, sourceFile, destinationContext, destinationTreePath):
        destinationDirectory = os.path.join(self.dirDestination, destinationContext, destinationTreePath)

        if not os.path.exists(destinationDirectory):
            os.makedirs(destinationDirectory)

        destinationFile = os.path.join(destinationDirectory, os.path.basename(sourceFile))

        if os.path.exists(destinationFile):
            destinationFile = self.buildDuplicateFileName(destinationFile)

        if self.command == ProcessType.COPY:
            shutil.copy2(sourceFile, destinationFile)
        else:
            shutil.move(sourceFile, destinationFile)

        print(sourceFile + " --> " + destinationFile)


    def buildDuplicateFileName(self, destinationFile):
        # parse file path
        file = os.path.basename(destinationFile)
        dir = os.path.dirname(destinationFile)
        base, ext = os.path.splitext(file)

        # get highest sequence number
        max = 0
        pattern = re.compile("^" + base + "\-(\d+)$")

        for f in os.listdir(dir):
            b = os.path.splitext(f)[0]

            match = pattern.match(b)

            if match is None:
                continue

            index = int(match.group(1))

            if index > max:
                max = index

        # build new incremental file name
        newFileName = str(base + "-{0}" + ext).format("%04d" % (max + 1))

        return os.path.join(dir, newFileName)


    def buildTreePath(self, metadata):
        if self.organizeBy == ProcessType.BY_SIZE:
            return self.buildTreePathBySize(metadata)
        else:
            return self.buildTreePathByDate(metadata)


    def buildTreePathBySize(self, metadata):
        return str(metadata.width) + "x" + str(metadata.height)


    def buildTreePathByDate(self, metadata):
        if metadata.dates.hasMetaDate():
            if self.buildTree:
                return metadata.dates.metaDate.strftime("%Y/%m/%d")
            else:
                return metadata.dates.metaDate.strftime("%Y-%m-%d")
        else:
            if not self.useFileTime:
                return "."

            if self.buildTree:
                return metadata.dates.fileDate.strftime("%Y/%m/%d")
            else:
                return metadata.dates.fileDate.strftime("%Y-%m-%d")


    def considerDimensionsLimit(self):
        if not self.organizeBy == ProcessType.BY_SIZE:
            return False

        if self.minWidth is not None and self.minWidth > 0:
            return True
        elif self.minHeight is not None and self.minHeight > 0:
            return True
        else:
            return False


    def toString(self):
        sb = []
        sb.append("command               = " + str(ProcessType.key(self.command).lower()))
        sb.append("organize by           = " + str(ProcessType.key(self.organizeBy).lower()))
        sb.append("source directory      = " + self.dirSource)
        sb.append("destination directory = " + self.dirDestination)
        sb.append("minimum image width   = " + str(self.minWidth))
        sb.append("minimum image height  = " + str(self.minHeight))
        sb.append("build tree            = " + str(self.buildTree))
        sb.append("use file time         = " + str(self.useFileTime))

        return "\n".join(sb)


class ImageMetadata():
    def __init__(self, file, type):
        self.file = file
        self.type = type
        self.width = None
        self.height = None
        self.dates = ImageDate()


    def parse(self):
        image = Image.open(self.file)

        self.extractDimensions(image)
        self.extractDate(image)


    def extractDimensions(self, image):
        self.width, self.height = image.size


    def extractDate(self, image):
        try:
            exif = image._getexif()
            self.extractDatetimeFromExif(exif)
        except AttributeError:
            self.extractDatetimeFromFile()
	except IndexError:
	    self.extractDatetimeFromFile()
	except Exception as e:
	    raise AttributeError("Unable to extrct date from " + self.file + " due to (" + e.message + ")")

    def extractDatetimeFromExif(self, exif):
        try:
            date = exif[0x9003]
            self.dates.metaDate = datetime.strptime(date, "%Y:%m:%d %H:%M:%S")
        except TypeError:
            raise AttributeError("no DateTimeOriginal EXIF marker found")
        except KeyError:
            raise AttributeError("no DateTimeOriginal EXIF marker found")


    def extractDatetimeFromFile(self):
        ctime = os.path.getctime(self.file)
        mtime = os.path.getmtime(self.file)
        date = ctime if ctime < mtime else mtime

        self.dates.fileDate = datetime.fromtimestamp(date)


    def matchesMinimumDimensions(self, minWidth, minHeight):
        if minWidth is not None:
            matchesMinWidth = self.width >= minWidth
        else:
            matchesMinWidth = True

        if minHeight is not None:
            matchesMinHeight = self.height >= minHeight
        else:
            matchesMinHeight = True

        return matchesMinWidth and matchesMinHeight


    def toString(self):
        sb = []
        sb.append("file=" + self.file)
        sb.append("type=" + self.type)
        sb.append("width=" + str(self.width))
        sb.append("height=" + str(self.height))
        sb.append("date=" + self.dates.toString())

        return "[" + ",".join(sb) + "]"


class ImageDate():
    def __init__(self):
        self.metaDate = None
        self.fileDate = None


    def hasMetaDate(self):
        return self.metaDate is not None


    def hasFileDate(self):
        return self.fileDate is not None


    def toString(self):
        sb = []
        sb.append("metaDate=" + str(self.metaDate))
        sb.append("fileDate=" + str(self.fileDate))

        return "[" + ",".join(sb) + "]"


if __name__ == "__main__":
    commands = []
    commands.append(ProcessType.key(ProcessType.COPY).lower())
    commands.append(ProcessType.key(ProcessType.MOVE).lower())

    trueFalse = []
    trueFalse.append(str(True))
    trueFalse.append(str(False))

    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=commands, help="command type")

    subparsers = parser.add_subparsers(help="sub-command help")

    parserByDate = subparsers.add_parser("by-date", help="processes photos by date")
    parserByDate.add_argument("-ft", default=False, choices=trueFalse,
        help="use file's ctime or mtime when image doesn't contain a date metadata (default False)")
    parserByDate.add_argument("-bt", default=False, choices=trueFalse, help="build tree")
    parserByDate.set_defaults(which=ProcessType.BY_DATE)

    parserBySize = subparsers.add_parser("by-size", help="processes photos by dimensions")
    parserBySize.add_argument("-mw", default=None, type=int, help="minimum image width")
    parserBySize.add_argument("-mh", default=None, type=int, help="minimum image height")
    parserBySize.set_defaults(which=ProcessType.BY_SIZE)

    parser.add_argument("ds", default=None, help="source directory")
    parser.add_argument("dd", default=None, help="destination directory")

    args = parser.parse_args()

    mp = OrganizeImages(os.path.realpath(args.ds), os.path.realpath(args.dd))
    mp.command = ProcessType.val(args.command)
    mp.organizeBy = args.which

    if mp.organizeBy == ProcessType.BY_SIZE:
        mp.minWidth = args.mw
        mp.minHeight = args.mh
    else:
        mp.buildTree = args.bt
        mp.useFileTime = args.ft

    print(mp.toString())

    mp.process()
