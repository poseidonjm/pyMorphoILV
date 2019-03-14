# Userspace Morpho ILV Driver

ILV protocol implementation in python to communicate with fingerprint readers from userspace using PyUSB

## Supported operations
- [x] Get info
- [x] Get fingerprint
- [ ] Manage local database
- [ ] Local Validation
- [ ] Local identification

## Supported readers
- MSO 300
- MSO CBM

---
Test program with CLI included

### Reference documentation of ILV protocol:
- [MorphoSmart™ Host System Interface specifications](https://www.emssa.net/source/content/Safran/MA500/Morphoaccess%20HSI%20Specification%205.41%20.pdf)
- [MorphoSmart™ Fingerprint scanners Installation Guide](http://www.impro.net/downloads/WebSiteDownloads/documentation/manuals/morpho/Unpublished/installation/MorphoSmart-InstallationGuide.pdf)

- [Find Devices](https://www.orangecoat.com/how-to/use-pyusb-to-find-vendor-and-product-ids-for-usb-devices)
- [libusb for windows](https://sourceforge.net/projects/libusb-win32/files/libusb-win32-releases/1.2.6.0/)
- [Python 2.7](https://www.python.org/downloads/release/python-2716/)

