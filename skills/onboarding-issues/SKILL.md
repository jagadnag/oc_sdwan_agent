---
name: onboarding-issues
description: Onboarding Issues - New device provisioning and deployment troubleshooting
license: MIT
compatibility: opencode
---

# Onboarding Issues

## Onboarding Process
1. Device boots and obtains IP
2. Device contacts vBond
3. vBond redirects to vManage
4. Device authenticates
5. Device downloads certificate
6. Device joins fabric

## Common Issues
- vBond unreachable
- DHCP failures
- Certificate installation failure
- Authentication failure
- Fabric membership failure

## Diagnostics
- Verify connectivity to vBond
- Check DHCP configuration
- Validate certificate
- Verify credentials
- Monitor onboarding logs

## Resolution
- Restore connectivity
- Fix DHCP
- Update certificates
- Validate credentials
- Monitor joining process
