# Dokku server setup

## Create server

* Make a server (on Linode).
  * Needs at least 2GB RAM for the build step or it crashes out (with code 137 - OOM).
  * Select the "Private IP" add-on.
  * Select "microcosm.cc" as the firewall.
* Set up the DNS in Cloudflare.
  * Add record for `wpy03`, use its public IP address, no CF proxying, default TTL.

### Internal ip address

The new server's private IP address should be added to `/etc/hosts` on `lb` & `api`, e.g.:

```
192.168.0.11 wpy03.microcosm.cc
```

### Enable firewall

```bash
# ssh
sudo ufw allow 2020

# python server
# from api
sudo ufw allow from 192.168.165.21 to any port 9000
# from lb
sudo ufw allow from 192.168.207.198 to any port 9000

# prometheus-node-exporter
# from api
sudo ufw allow from 192.168.165.21 to any port 9100
# from lb
sudo ufw allow from 192.168.207.198 to any port 9100

# optional dev alias for python server
sudo ufw allow 80

sudo ufw enable
```

### Enable prometheus

```bash
sudo apt install prometheus-node-exporter
```

and configure by editing `/etc/prometheus/prometheus.yml` on the api server like this:

```yaml
...
  - job_name: node
    # If prometheus-node-exporter is installed, grab stats about the local
    # machine by default.
    static_configs:
    - targets: ['api.microcosm.cc:9100','wpy01.microcosm.cc:9100','wpy02.microcosm.cc:9100','wpy03.microcosm.cc:9100']
...
```


## Create users

Create all users as appropriate, e.g.

```bash
# create users
adduser madwort
# add sudo
usermod -aG sudo madwort
# add ssh key
sudo su - madwort
ssh-import-id gh:madwort
```

### Create a user for the docker app

So that we don't have to run the docker app as root, create a user for it:

```bash
sudo useradd -Ms /bin/bash -u1100 microweb
```

The uid should match the one in the Dockerfile, which currently looks like:

```
RUN useradd -Ms /bin/bash -u1100 microweb
USER microweb
```

## Update hosts file

Copy `/etc/hosts` from an existing `wpy*` server - it contains a set of overrides to send traffic direct to the load balancer's private IP.

## Install Dokku

based on https://dokku.com/docs/getting-started/installation/

```bash
# for debian systems, installs Dokku via apt-get
wget -NP . https://dokku.com/install/v0.35.16/bootstrap.sh
sudo DOKKU_TAG=v0.35.16 bash bootstrap.sh

# add a key
cat id_rsa.pub | dokku ssh-keys:add admin

# install dokku-memcached plugin
sudo dokku plugin:install https://github.com/dokku/dokku-memcached.git --name memcached
dokku memcached:create microweb-memcached
```

## Create microweb app

Create the app on the server:

```bash
dokku apps:create microweb
```

and link it to the memcached app:

```bash
dokku memcached:link microweb-memcached microweb
```

Push to the app from your local git repository:

```bash
git remote add wpy03 dokku@lfgssdemo:microweb
git push wpy03 main
# nb. if you're pushing a wip branch!
git push wpy03 HEAD:main
```

Configure some things on the server:

```bash
# serve on port 9000 for consistency with previous servers
dokku ports:add microweb http:9000:5000

dokku domains:add microweb *.microcosm.app
# if you need to access the server directly for testing, also add explicit lfgss domains
dokku domains:add microweb lfgss.com
dokku domains:add microweb www.lfgss.com

dokku network:create microweb-network
dokku network:set microweb initial-network microweb-network

dokku config:set --no-restart microweb DJANGO_SETTINGS_MODULE=microweb.settings
dokku config:set --no-restart microweb PYTHONPATH=.
dokku config:set --no-restart microweb MEMCACHE_HOST=dokku-memcached-microweb-memcached
dokku config:set --no-restart microweb CLIENT_SECRET=123456
# use single quotes if you have special chars!
dokku config:set --no-restart microweb SECRET_KEY='!aoeui12345'
# Optional: a Thunderforest tile key turns on the event maps' OpenCycleMap and
# Landscape layers. Without one the maps offer OpenStreetMap's standard tiles.
# dokku config:set --no-restart microweb THUNDERFOREST_API_KEY=abc123
# Optional: `requests` uses the bundled certifi CA store, which is kept current.
# Set this only if you need the system CA bundle instead (e.g. private CAs).
# dokku config:set --no-restart microweb REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
```

Add some nginx config:

```bash
dokku nginx:set microweb proxy-connect-timeout 90s
dokku nginx:set microweb proxy-send-timeout 90s
dokku nginx:set microweb proxy-read-timeout 90s
dokku nginx:set microweb proxy-buffers "32 4k"
dokku nginx:set microweb client-max-body-size 30m
# nb. if forwarded-proto is set to $scheme, gunicorn sees http
dokku nginx:set microweb x-forwarded-proto-value https
# need to run a rebuild for this config to take effect
dokku ps:rebuild microweb
```

Add some CloudFlare / nginx configuration for the app

```bash
mkdir /home/dokku/microweb/nginx.conf.d/
```

Copy this block into a file at `/home/dokku/microweb/nginx.conf.d/cloudflare.conf`:

```
  # Cloudflare
  set_real_ip_from 103.21.244.0/22;
  set_real_ip_from 103.22.200.0/22;
  set_real_ip_from 103.31.4.0/22;
  set_real_ip_from 104.16.0.0/12;
  set_real_ip_from 108.162.192.0/18;
  set_real_ip_from 141.101.64.0/18;
  set_real_ip_from 162.158.0.0/15;
  set_real_ip_from 172.64.0.0/13;
  set_real_ip_from 173.245.48.0/20;
  set_real_ip_from 188.114.96.0/20;
  set_real_ip_from 190.93.240.0/20;
  set_real_ip_from 197.234.240.0/22;
  set_real_ip_from 198.41.128.0/17;
  set_real_ip_from 199.27.128.0/21;
  set_real_ip_from 2400:cb00::/32;
  set_real_ip_from 2405:8100::/32;
  set_real_ip_from 2405:b500::/32;
  set_real_ip_from 2606:4700::/32;
  set_real_ip_from 2803:f800::/32;
  real_ip_header CF-Connecting-IP;
```

Then ensure file permissions are correct & reload nginx.

```bash
chown dokku:dokku /home/dokku/microweb/nginx.conf.d/cloudflare.conf
service nginx reload
```

Finally restart the app on the server to pick up all the changes:

```bash
# restart
dokku ps:restart microweb
```

Then attach to the load balancer, by editing `/etc/nginx/nginx.conf` on the lb server.

And maybe check the logs for errors as the requests roll in!

```bash
# check the application logs
dokku logs microweb
# check the nginx logs
tail /var/log/nginx/microweb-error.log
```

If you need to restart memcached, you can use:

```bash
dokku memcached:restart microcosm-memcached
```

## Maintaining / updating running server

### Enabling/disabling a server

On the lb server, in `/etc/nginx/nginx.conf`, there is a block like:

```
        # microweb is https?://*.microcosm.app
        upstream microweb  {
                server 192.168.129.5:9000;   # wpy01
                server 192.168.198.69:9000;  # wpy02
                # server 192.168.198.188:9000; # wpy03
        }
```

You should be able to bring servers in & out of rotation just by commenting/uncommenting the relevant line & reloading this nginx config (`sudo service nginx reload`).

### Updating the server

To update from a local git repository, check out this repo and then:

```bash
# remote add only needs doing the first time you clone the repo
git remote add wpy03 dokku@lfgssdemo:microweb
git push wpy03 main
```

You should see dokku use the `Dockerfile` to build a new image & switch it into production.
If the docker build errors for whatever reason, dokku should keep using the current image.

#### Continuous deployment

If we feel confident, we can generate a deployment SSH key & do the git push automatically from GitHub every time we merge a PR.  
