cd ../clash
nohup ./clash -d . > ./clash.log 2>&1& echo $! > ./clash.pid
