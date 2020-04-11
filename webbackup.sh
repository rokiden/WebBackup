#!/bin/bash

if [[ $# -ne 3 ]] && [[ $# -ne 4 ]]; then
  echo "Usage: $(basename $0) dir_path webdav user [backup_name]"
  exit 0
fi

backup_dir=$1
webdav=$2
user=$3

if [ -n "$4" ]; then
  backup_name=$4
else
  backup_name=$(basename $backup_dir)
fi

backup_path="/var/tmp/"$backup_name"_$(date +%Y%m%d-%H%M%S).tar.gz"
backup_ts="/var/tmp/"$backup_name"_ts"

curl_url="$webdav/"$(basename $backup_path)

if [ -f "$backup_ts" ]; then
  echo "Timestamp file found, find newer..."
  [[ ! -z $(find $backup_dir -type f -newer $backup_ts) ]] && new_found=true || new_found=false
else
  echo "Timestamp file not found"
  new_found=true
fi

if $new_found; then
  echo "Backuping..."
  echo $backup_path
  tar -cvzf $backup_path $backup_dir
  if [ $? -eq 0 ]; then
    echo "Uploading..."
    curl --fail -T $backup_path -u $user $curl_url && echo "Curl ok" || echo "Curl error"
    touch $backup_ts
    if [ $? -ne 0 ]; then
      echo "Can't touch ts" >&2
    fi
  else
    echo "tar error" >&2
  fi
  echo "Cleanup..."
  rm $backup_path
else
  echo "Backup skipped"
fi
