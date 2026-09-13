# Sub-doc 80. Stateful Services and Quorum (etcd / Patroni / Redis Sentinel / MinIO / Consul server)

Section 1 Item C and Section 7 of `ENGINEERING_PRINCIPLES.md` are prerequisites for this file. The baseline date is 2026-08-18.

## Section 1. Common Quorum Rules

1. **Member Count and Distribution**. The member count MUST be odd. A majority of members MUST NOT share one failure domain (physical host, rack, or availability zone). The placement rule MUST be readable in the declared configuration.

2. **Membership Change**. A membership change MUST move one member per step. The new member MUST join and MUST finish sync before the old member is removed. One step MUST NOT replace a majority of members. The next change MUST NOT start until the current change has finished.

3. **Split-brain Handling**. On a split brain or a lost majority, the response MUST be a recorded human procedure. Automation MUST NOT pick a survivor and force a rebuild. Section 2 Item C of `ENGINEERING_PRINCIPLES.md` applies.

4. **Backup Before Change**. A change that touches the quorum layer MUST wait for a backup that has already been restored successfully. Section 7 Item D of `ENGINEERING_PRINCIPLES.md` applies.

## Section 2. etcd

1. **v2 API Removed**. etcd 3.6.0 removed the `--enable-v2` flag. v3store is the only membership source of truth. When v2store still holds data other than membership, etcd refuses to start. From 3.5.18, `etcdutl check v2store` exists for a pre-migration check.

    Official source URL is <https://etcd.io/blog/2025/announcing-etcd-3.6/>

2. **Other Breaking Changes**. From etcd 3.6.0 a peer endpoint no longer serves client requests. `etcdctl` and `etcdutl` have separate duties. An old binary is not compatible with a new schema. Before the executing Agent writes an operations script, the executing Agent MUST confirm the target version.

3. **Data Directory**. An etcd data directory is a durable tier. That directory MUST sit on dedicated low-latency storage. That device MUST NOT be shared with another write-heavy service.

4. **Backup**. `etcdctl snapshot save` MUST run on a schedule. The snapshot MUST live outside the etcd cluster failure domain. Section 9 Item B of `ENGINEERING_PRINCIPLES.md` applies. The restore procedure MUST be drilled on a schedule.

5. **Compaction and Defragmentation**. Automatic compaction MUST be set explicitly. The default MUST NOT be the only setting. `defrag` is a blocking operation. `defrag` MUST run one node at a time and MUST avoid a quorum boundary.

## Section 3. Patroni

### Item A. DCS Configuration Section

When Patroni talks to etcd 3.6 or newer, the Patroni configuration MUST use the `etcd3` section. The `etcd` section uses the removed v2 API and fails during member discovery.

Official source URLs are <https://patroni.readthedocs.io/en/latest/> and <https://github.com/patroni/patroni/issues/3382>

A key written with the v2 protocol is not visible to the v3 protocol. Switching the protocol is equivalent to changing the DCS contents and MUST follow Section 1 item 4 of this file (Backup Before Change).

1. **DCS Is Upstream**. Patroni reads the DCS and writes a lease. PostgreSQL is downstream of Patroni. Automation inside PostgreSQL MUST NOT write back into the DCS.

2. **Configuration Source**. Cluster-level settings such as `postgresql.parameters` MUST have one owner, and that owner is the dynamic configuration in the DCS. The local `patroni.yml` MAY hold only node-local items. The same parameter MUST NOT be defined in both places. Section 5 Item A of `ENGINEERING_PRINCIPLES.md` applies.

3. **Manual Intervention**. While `patronictl pause` is in effect, automation MUST NOT change that cluster. A switch MUST use `patronictl switchover`. `failover` is allowed only after the primary is confirmed down.

4. **Version Compatibility**. Patroni 4.1.x supports PostgreSQL 9.3 through 18. Before use, the executing Agent MUST confirm that the target PostgreSQL version sits inside that range.

## Section 4. Redis Sentinel

1. **Sentinel Count and Distribution**. The Sentinel count MUST be odd and MUST be at least 3. A majority of Sentinel instances MUST NOT share a failure domain with the Redis instances that those Sentinels watch. `quorum` MUST be set explicitly and MUST be less than or equal to the Sentinel majority.

2. **Configuration Gets Rewritten**. Sentinel rewrites its own config file at runtime (the current primary and the known replicas). A configuration-management tool MUST NOT force-overwrite that file on every run. Ansible MAY create the initial file. After that create, a template overwrite is forbidden, because that overwrite breaks the zero-drift premise in Section 2 Item A of `ENGINEERING_PRINCIPLES.md`. This exception MUST be a named entry in `planning/decisions.md`.

3. **Client**. A client MUST discover the primary address through Sentinel. A hard-coded primary address is forbidden.

4. **Durability Awareness**. Redis replication is asynchronous. A requirement for zero data loss MUST NOT be met with Redis Sentinel. That judgment MUST be recorded as an architecture decision.

## Section 5. MinIO and Object Storage

### Item A. Upstream Status

The MinIO community edition lost admin-console management functions in 2025. The public repository was archived read-only on 2026-04-25. After that date there is no official community binary and no upstream patch. Server code remains AGPLv3.

Official source URL is <https://github.com/minio/minio>

Before a new system selects the MinIO community edition, `planning/decisions.md` MUST record three items. The three items are who builds and patches CVEs, the AGPLv3 compliance judgment, and the migration path. An existing deploy MUST have a retirement schedule.

1. **Erasure Set Distribution**. Members of an erasure set in a distributed deploy MUST span physical hosts. A single-host failure MUST NOT take read ability away from any erasure set.

2. **Disk and Node Expansion**. MinIO expands by adding a server pool. Adding or removing a disk inside an existing set is not that expansion. Expansion planning MUST finish before the change. That change is irreversible under Section 7 Item D of `ENGINEERING_PRINCIPLES.md`.

3. **As a Terraform Backend**. When S3-compatible storage is a Terraform backend, the executing Agent MUST confirm that the implementation supports a conditional write (`If-None-Match`). `use_lockfile` depends on that capability. When the implementation lacks that capability, the lock does not take effect, and that pairing is forbidden in a multi-person environment.

## Section 6. Consul server

1. **Server and Client Separation**. A Consul server and a client agent have separate duties. A server node MUST NOT run a workload.

2. **Auto-bootstrap**. `bootstrap_expect` is allowed only during first create. After create finishes, that setting MUST be removed from the configuration. Leaving that setting in place is forbidden.

3. **Snapshot**. `consul snapshot save` MUST run on a schedule. The snapshot MUST live outside the cluster failure domain.

4. **Service Registration and KV Boundary**. When KV is a configuration source, Section 5 Item A of `ENGINEERING_PRINCIPLES.md` applies. Each key MUST have one writer. Two systems MUST NOT write the same key prefix at the same time.
