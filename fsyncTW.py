import os
import argparse

def fsyncTW(rootDir):
    for dirname, dirnames, filenames in os.walk(rootDir):
        for filename in filenames:
            filePath = os.path.join(dirname, filename)
            print 'sync %s' % filePath
            os.fsync(os.open(filePath, os.O_RDONLY))

if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument('syncpoint', help='folder to recursively run fsync()')
	args = parser.parse_args()
	fsyncTW(args.syncpoint)