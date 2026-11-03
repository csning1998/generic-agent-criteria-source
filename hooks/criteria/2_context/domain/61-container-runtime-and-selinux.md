# Sub-doc 61. Container Runtime (OCI / Rootless Podman / Docker / SELinux)

Sections 6 and 8 of `ENGINEERING_PRINCIPLES.md` are prerequisites for this file. The baseline date is 2026-08-18.

## Section 1. OCI Artifacts

1. **Reference by Digest**. A production image reference MUST use the form `image@sha256:...`. A tag MAY exist as a human-readable label. Section 6 Item B of `ENGINEERING_PRINCIPLES.md` applies. The PreToolUse hook does not enforce that digest.

2. **Reproducible Build**. Every external input in a Containerfile MUST be pinned. That set includes the base-image digest, each package version, and the checksum of each downloaded file. `latest` is forbidden. A package install without a version is forbidden. `curl | sh` without a checksum is forbidden.

3. **Layering and Cache**. Build instructions MUST place a low-churn layer before a high-churn layer. Secret material MUST NOT be written into any layer, including an intermediate layer. A build-time secret MUST use a build-secret mount. A build arg MUST NOT carry a secret.

4. **Labels**. An image MUST carry the OCI labels `org.opencontainers.image.revision` (commit SHA), `.source`, `.created`, and `.base.digest`. Section 9 Item A of `ENGINEERING_PRINCIPLES.md` applies.

## Section 2. Rootless Podman

1. **Rootless by Default**. A single-node container workload MUST run rootless by default. A rootful case (macvlan or a specific device) MUST be a named entry in `planning/decisions.md`.

### Item B. Quadlet as the Unit Declaration Method

A systemd-managed container MUST be declared as a Quadlet unit file (`.container`, `.pod`, `.network`, `.volume`, or `.image`). `podman generate systemd` is deprecated and is forbidden. Quadlet requires cgroup v2.

Refer to <https://docs.podman.io/en/latest/markdown/podman-systemd.unit.5.html> for the official Podman Quadlet unit file reference.

A rootless Quadlet file MUST live on the systemd search path of that user and MUST be started by that user's systemd. A service-section `User=` line MUST NOT be used to imitate rootless.

1. **subuid / subgid**. `/etc/subuid` and `/etc/subgid` are part of the host declaration. Ansible MUST manage those files, and those files MUST be in version control. Two users MUST NOT receive overlapping ranges.

2. **Auto-update Boundary**. `AutoUpdate=registry` is allowed only on a stateless service that MAY restart at any time. A stateful service MUST pin a digest and MUST upgrade through a pipeline. Section 7 Item A of `ENGINEERING_PRINCIPLES.md` applies.

3. **Ports**. A rootless container MUST NOT bind a port below 1024. An external service MUST sit behind a front reverse proxy. A global relaxation of `net.ipv4.ip_unprivileged_port_start` is forbidden.

## Section 3. Docker

1. **Scope of Use**. When the architecture decision selects Podman, Docker MAY exist only on a developer workstation. A production host MUST NOT run both socket services.

2. **Socket**. `/var/run/docker.sock` MUST NOT be mounted into any container. A CI workload that needs to build MUST use a daemonless build tool.

3. **Compose Scope of Use**. A Compose file is allowed for local development. A Compose file MUST NOT be the deploy source of any environment. The same bound applies to Section 3 Item A of `52-packer-vagrant.md`.

## Section 4. SELinux

1. **Enforcing by Default**. SELinux on a production host MUST be `enforcing`. `permissive` is allowed only inside a time-bounded debug window, and that window MUST be recorded. `disabled` is forbidden as a remedy.

2. **Boolean Bypass Prohibited**. A global boolean such as `setsebool -P container_manage_cgroup on` MUST NOT be the fix for a single case, unless the meaning of that boolean matches the need and the change is recorded.

3. **Volume Labels**. A container mount MUST NOT carry the relabel option `:z`, `:Z`, or `relabel=`. A relabel walks the whole source tree and replaces the label of every file below the source path. A relabel of a parent directory therefore removes access from every running container which mounts a path below that directory. A host path which a container mounts MUST receive its label from a file context rule (`semanage fcontext` and `restorecon`).

4. **Custom Policy**. A custom policy MUST be a policy module (`.te` / `.fc`), MUST be in version control, and MUST be installed by Ansible. Raw `audit2allow` output MUST NOT be applied without review.

5. **SELinux on Kubernetes**. From Kubernetes v1.36, a SELinux volume mount applies the label with `mount -o context=` at mount time and no longer walks the tree. Before the executing Agent writes `seLinuxOptions`, the executing Agent MUST confirm the target cluster version and that mount behavior.

    Refer to <https://kubernetes.io/blog/2026/04/22/kubernetes-v1-36-release/> for the official Kubernetes v1.36 release notes.

6. **Agent Bind Mounts**. A command which the executing Agent runs MUST NOT bind mount a host path into a container through `-v`, `--volume`, or `--mount type=bind`, whether read only or writable. A script which the executing Agent writes for execution on the host, such as a hook copy, MUST NOT declare a host bind mount. A host bind mount produces an access vector cache denial when the host path and the container process carry incompatible SELinux labels. A file which a container requires MUST be transferred into the target container through `podman create` and `podman cp`. The executing Agent MUST NOT run `podman kube play` or a compose command, since both read mounts from a declaration file. `gate-check.py` denies a direct bind mount command, a kube play or compose command, and a script below a temporary directory which contains a host bind mount. `gate-check.py` does not inspect a script outside a temporary directory.

7. **Agent SELinux State Writes**. A command which the executing Agent runs, and a script which the executing Agent writes for execution on the host, MUST NOT write an SELinux label or change SELinux policy. The ban covers `chcon`, `restorecon`, `setfiles`, `chcat`, `semanage`, `setsebool`, and `semodule`, including a call through `sudo` or `podman unshare`, and the container option `--security-opt label=disable`. The executing Agent MUST report a needed label or policy change to the owner. `gate-check.py` denies these forms in a command and in a script below a temporary directory. A repository hook which runs `chcon` during `git commit` executes outside the inspection of `gate-check.py`.

## Section 5. Runtime Privileges

1. **Least Capability**. A container MUST start from `--cap-drop=ALL` and MUST add back only the capabilities that the process needs. `--privileged` is forbidden. `--security-opt label=disable` and `--security-opt seccomp=unconfined` MUST NOT be regular settings.

2. **Read-only Root Filesystem**. The container root filesystem MUST be read-only by default. A path that must be writable MUST be a named volume or a tmpfs mount.

3. **Non-root UID**. A process inside a container MUST NOT run as UID 0. The image MUST declare a non-root `USER` in the Containerfile. A runtime flag alone does not satisfy Section 5 item 3.
