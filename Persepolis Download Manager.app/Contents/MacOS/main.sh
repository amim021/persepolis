#!/bin/bash
export PATH=/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin
export PYTHONPATH=$PYTHONPATH:/usr/local/lib/python3.5/site-packages
run_times=`ps -A|grep "persepolis-down"|wc -l`
cd "/usr/local/share/persepolis"
echo $run_times
if [ "$run_times" -eq "1" ];then
	exec ./"Persepolis Download Manager" "persepolis-download-manager" --execute yes 2> /tmp/persepolis_error
else
	exec ./"Persepolis Download Manager" "persepolis-download-manager" --execute no
fi
exit
