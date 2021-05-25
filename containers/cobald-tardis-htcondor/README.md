# `COBalD/TARDIS` and HTCondor Overlay Batch System Image

This docker image provides a fully configurable `COBalD/TARDIS` installation combined with a HTCondor installation to be
used to integrate resources into a HTCondor overlay batch system.

## Configure `COBalD/TARDIS`

You can configure `COBalD/TARDIS` as described in the [documentation](https://cobald-tardis.readthedocs.io/en/latest/) 
and bind mount it into the containers `/srv` directory. The configuration directory must contain a valid `cobald.yml` 
configuration and depending on the configuration, it will be used to store the persistent state as well as logs of the 
COBalD/TARDIS installation (see the [documentation](https://cobald-tardis.readthedocs.io/en/latest/) for details). 

```bash
docker run -v $PWD/configuration:/srv matterminers/cobald-tardis-htcondor:latest
```

## HTCondor Token Support

Starting with the production release series 9.0 HTCondor introduces a new security configuration, which is no longer 
host-based. The security configuration is now user-based and requires authentication to access the HTCondor pool. This
is also true for read-only operations like calling `condor_status`.

### Managing Tokens
This docker images supports the ID tokens authentication method introduced with the HTCondor 9.0 series. 

In order to use ID tokens add any tokens provided by the operator of the overlay batch system to a `tokens.d` directory
and bind mount it to `/etc/condor/tokens.d`. HTCondor is automatically using them authenticate against the pool.

```bash
docker run -v $PWD/tokens.d:/etc/condor/tokens.d matterminers/cobald-tardis-htcondor:latest
```

Since `COBald/TARDIS` uses the `condor_status` command, the token added needs at least the `ALLOW_READ` privilege to 
access the HTCondor Collector and to query the status of resources.

In addition, `COBalD/TARDIS` uses the `condor_drain` command to release under utilized resources. Therefore, a second 
token to access the HTCondor StartD of the Drone is needed.

Usually, both tokens are provided by the operator of the HTCondor overlay batch system.
