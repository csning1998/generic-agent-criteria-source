# Sub-doc 71. On-Premises Virtualization (Libvirt / QEMU-KVM / vSphere / Nutanix)

Sections 1, 6, and 7 of `ENGINEERING_PRINCIPLES.md` are prerequisites for this file. The baseline date is 2026-08-18.

## Section 1. Common Rules

1. **Virtualization Layer Is Upstream**. The hypervisor, the storage pool, and the virtual network are upstream. A virtual machine and the workload inside that virtual machine are downstream. Section 1 Item B of `ENGINEERING_PRINCIPLES.md` applies. Automation inside a virtual machine MUST NOT change a hypervisor setting.

2. **Explicit Host Distribution**. Placement of a virtual machine on a physical host MUST be readable in the declared configuration (an anti-affinity rule, a host group, or a placement policy). Section 1 Item C of `ENGINEERING_PRINCIPLES.md` applies. A majority of members of a quorum component MUST NOT share one physical host or one storage pool.

3. **Image Source**. A virtual machine MUST be created from an immutable image. See `52-packer-vagrant.md`. Cloning an already-running machine as the create method is forbidden. That method cannot trace the source and violates Section 9 Item A of `ENGINEERING_PRINCIPLES.md`.

4. **Snapshots Are Not Backups**. A snapshot is a short-lived recovery point and MUST have an expiry. A snapshot MUST NOT count as the recovery path in Section 7 Item D of `ENGINEERING_PRINCIPLES.md`. A backup MUST be a data copy that does not live only on the virtualization layer.

## Section 2. Libvirt / QEMU-KVM

1. **Domain Definition as Declaration**. Domain XML MUST be produced by Terraform (`libvirt` provider) or by Ansible, and MUST be in version control. `virsh edit` MUST NOT be the long-term source of a setting.

2. **Storage Pool and Volume**. The declaration of a storage pool and a volume MUST be separate from the declaration of the virtual machine. Deleting a virtual machine MUST NOT delete a durable data volume unless that delete is explicit. Section 1 Item A of `ENGINEERING_PRINCIPLES.md` applies.

3. **CPU Model**. The CPU model MUST be set explicitly and MUST be the same across the cluster. `host-passthrough` follows the hardware of the current host and MUST NOT be the setting of a workload that must migrate, unless a no-migration record already exists.

4. **First Boot Configuration**. cloud-init or Ignition MAY perform only the three classes listed in Section 1 Item B of `52-packer-vagrant.md`.

## Section 3. vSphere

1. **Licensing and Version Changes**. After the Broadcom acquisition, VMware licensing and packaging changed more than once. Before the executing Agent states a version, a license term, a product name, or a support window, the executing Agent MUST verify the current official source. This file does not pin those details. After that verification fails, the executing Agent MUST write `目前缺乏足夠的最新資訊`.

2. **Provider Permissions**. The service account used by the `vsphere` provider MUST be a least-privilege role. The `Administrator` role is forbidden. The grant MUST be limited to the target datacenter and folder.

3. **Templates**. A virtual machine MUST be created from a template or from a Content Library item. That template MUST be produced by Packer and MUST carry a version. A long-lived template maintained by hand is forbidden.

4. **Anti-affinity**. A DRS anti-affinity rule MUST be declared in code. A click in the UI MUST NOT be the source of that rule. Section 9 Item A of `ENGINEERING_PRINCIPLES.md` applies.

## Section 4. Nutanix

1. **Management Plane Boundary**. Prism Central is the upstream management plane. Automation in a workload layer MUST NOT change Prism Central cluster registration or a storage-container setting.

2. **Provider and API Version**. The pairing of the `nutanix` provider and the Prism API MUST be verified and then recorded. This file does not pin a current recommended pair. After that verification fails, the executing Agent MUST write `目前缺乏足夠的最新資訊`.

3. **Distribution**. Placement of a virtual machine on a node follows Section 1 Item B of this file. Affinity and anti-affinity MUST be declared as policy.

## Section 5. Networking

1. **VLAN and Subnet Are Upstream**. VLAN assignment and subnet planning are upstream declarations and MUST have one owner. Section 5 Item A of `ENGINEERING_PRINCIPLES.md` applies. A virtual-machine declaration MAY reference a subnet. A virtual-machine declaration MUST NOT define a new subnet.

2. **IP Allocation**. The repository MUST choose one IP allocation method (a DHCP reservation, IPAM, or a static address) and MUST record that choice. Two methods MUST NOT mix inside one environment without a written boundary.
