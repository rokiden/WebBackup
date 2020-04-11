import sys
import re
import argparse
from typing import List
import owncloud

default_pattern = r'.*\.tar\.gz'
default_max_cnt = 30
default_max_size = 10 * 2 ** 10  # 10GB
default_free_inc_perc = 10


def rotate(cloud_url, user, password, backup_dir, backup_pattern=default_pattern, max_cnt=default_max_cnt,
           max_size=default_max_size,
           free_inc_perc=default_free_inc_perc):
    oc = owncloud.Client(cloud_url)
    oc.login(user, password)

    files: List[owncloud.FileInfo] = oc.list(backup_dir)

    # filter files by pattern
    if len(backup_pattern) > 0:
        backups = [f for f in files if re.match(backup_pattern, f.get_name())]
    else:
        backups = files

    if not backups:
        print('backups not found')
        return

    # sort by filename, newer first
    backups = sorted(backups, reverse=True, key=lambda f: f.get_name())

    # calculate cumulative size
    cum_size = 0
    for b in backups:
        cum_size = b.get_size() + cum_size
        b.attributes['cum_size'] = cum_size
    print('backups found: %d %.02fMB' % (len(backups), backups[-1].attributes['cum_size'] / 2 ** 20))

    # calculate target free space as size of last backup + 10%
    target_free = backups[0].get_size() * (100 + free_inc_perc) / 100
    # calculate target used
    target_used = max_size * 2 ** 20 - target_free
    print('target used: %.02fMB free: %.02fMB' % (target_used / 2 ** 20, target_free / 2 ** 20))

    # list for deletion
    del_list = set()

    number_exceeded = len(backups) > max_cnt
    if number_exceeded:
        print('number exceeded')
        del_list.update(backups[max_cnt:])

    size_exceeded = backups[-1].attributes['cum_size'] > target_used
    if size_exceeded:
        print('size exceeded')
        for b in reversed(backups):  # older first
            if b.attributes['cum_size'] > target_used:
                del_list.add(b)
            else:
                break

    # delete files from server
    deleted = 0
    for d in sorted(del_list, key=lambda f: f.get_name()):  # sort for log readability
        if d == backups[0]:  # protect latest backup
            print("ATTENTION! Attempt to delete latest backup", file=sys.stderr)
            continue
        print('delete', d.get_name())
        oc.delete(d.path)
        deleted += 1
    oc.logout()

    print('deleted: %d' % (len(del_list)))


if __name__ == '__main__':
    argparser = argparse.ArgumentParser()
    argparser.add_argument('cloud_url', metavar='URL', help='cloud URL')
    argparser.add_argument('user', metavar='USER', help='username')
    argparser.add_argument('passwd', metavar='PASS', help='password')
    argparser.add_argument('dir', metavar='DIR', help='backup directory')
    argparser.add_argument('-p', '--pattern', help='backup filename pattern', default=default_pattern)
    argparser.add_argument('-n', '--max-cnt', type=int, help='max backups number', default=default_max_cnt)
    argparser.add_argument('-s', '--max-size', type=int, help='max backups size, MB', default=default_max_size)
    argparser.add_argument('-i', '--free-inc', type=int, help='target free space = last backup size + FREE_INC %%',
                           default=default_free_inc_perc)
    args = argparser.parse_args()

    rotate(args.cloud_url, args.user, args.passwd, args.dir, args.pattern, args.max_cnt, args.max_size, args.free_inc)
