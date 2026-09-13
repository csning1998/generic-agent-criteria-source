# Sub-doc 52. Packer / Vagrant / Image Build

Sections 1 through 9 of `ENGINEERING_PRINCIPLES.md` apply to this file. Section 6 of `ENGINEERING_PRINCIPLES.md` (immutability and supply chain) is the primary section. The baseline date is 2026-08-18.

## Section 1. Build and Runtime Separation

1. **Complete at Build Time**. Package installation, kernel parameters, SELinux policy-module load, and enablement of a base service MUST finish during the Packer build. An install that runs after boot violates Section 6 Item D of `ENGINEERING_PRINCIPLES.md`.

2. **Runtime Only Binds**. First boot MAY perform only three classes of work. The three classes are host identity (hostname and machine-ID regeneration), network binding, and identity fetch (a short-lived credential). First boot MUST NOT install software.

3. **Machine Identity Regeneration**. The image MUST clear `/etc/machine-id`, SSH host keys, and any cloud-agent instance cache. Leaving those values in the image causes multiple instances to share one identity and violates Section 8 Item B of `ENGINEERING_PRINCIPLES.md`.

## Section 2. Packer-Specific

1. **Plugin Pinning**. The `packer {}` block MUST declare `required_plugins` and MUST pin each plugin version. Packer has shipped plugins apart from the core since 1.7. An unpinned plugin lets the build drift over time.

2. **Reproducible Build Input**. A source image MUST be named by an immutable identifier (an AMI ID, an OCI digest, or an ISO checksum). `most_recent = true` is forbidden. An ISO source MUST set `iso_checksum`.

3. **Provisioner Boundary**. When Packer calls Ansible, that role MUST also be runnable on an already-built host. A role that is true only inside the Packer environment, such as a role that assumes a path under `/tmp` already exists, is forbidden.

4. **Output Tagging**. An image MUST carry traceable tags. The required tags are the source commit SHA, the build time, the base-image identifier, and the Packer version. Section 9 Item A of `ENGINEERING_PRINCIPLES.md` applies.

## Section 3. Vagrant-Specific

1. **Scope of Use**. Vagrant is allowed for local development and local verification. Vagrant MUST NOT be a deploy path for any environment. A setting in a `Vagrantfile` MUST NOT be the source of a production setting.

2. **Box Pinning**. `config.vm.box_version` MUST be pinned. An unpinned public box MUST NOT be the baseline for a verification.

3. **Parity with Production**. The Ansible role that a Vagrant environment applies MUST be the same role that production applies. A difference MAY exist only in inventory variables. A condition such as `when: vagrant` inside a role violates Section 3 Item B of `ENGINEERING_PRINCIPLES.md`.

## Section 4. Image Lifecycle

1. **Versioning and Retention**. Image versions MUST increase monotonically. The retention window of an old image MUST be stated and MUST outlast the longest recovery window. Section 7 Item D of `ENGINEERING_PRINCIPLES.md` applies.

2. **Replacement**. When a CVE fix lands, instances MUST be replaced by a new image. An in-place patch that is then left in service is forbidden. An in-place patch is allowed only as an emergency stop, and the same working day MUST replace that instance with a new image.
