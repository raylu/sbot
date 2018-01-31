## sbot

a discord bot

### setup

set up an app at https://discordapp.com/developers/applications/me
```
pip3 install -r requirements.txt
cp config.yaml{.example,}
$EDITOR config.yaml
./sbot
```

#### code eval

make the nsjail directory a sibling of the pbot directory:
```
cd ..
git clone --recursive git://github.com/google/nsjail.git
cd nsjail
make
```

if /sys/fs/cgroup/memory doesn't exist:
```
sudo mkdir /sys/fs/cgroup/{memory,pids}
sudo mount -t cgroup memory -o memory /sys/fs/cgroup/memory
sudo mount -t cgroup pids -o pids /sys/fs/cgroup/pids
```

set up NSJAIL memory/pids cgroups:
```
sudo mkdir /sys/fs/cgroup/{memory,pids}/NSJAIL
sudo chown -R $USER: /sys/fs/cgroup/{memory,pids}/NSJAIL
```

#### EVE price checker

install postgresql  
edit `/etc/postgresql/9.6/main/pg_hba.conf` to change the local/all/all/peer user to local/all/all/trust  
`sudo service postgresql restart`  
download postgres-latest.dmp.bz2 from https://www.fuzzwork.co.uk/dump/
```
sudo -u postgres psql
	create database eve;
	create user sbot;
	grant all privileges on database eve to sbot;
bunzip2 -c postgres-latest.dmp.bz2 | pg_restore -U sbot -d eve -c -t mapSolarSystems -t mapRegions -t invGroups -t invTypes
```
