# Master SD Image Capture Process

Follow these steps to turn your current RPi into a "Golden Image" for production cloning.

## 1. Sanitize the RPi (On the RPi)
Run the `prepare_master.sh` script. This will:
- Stop the services.
- Delete temporary logs and caches.
- Remove SSH host keys (so every clone generates its own).
- Clear command history.

## 2. Shutdown the RPi
```bash
sudo shutdown -h now
```

## 3. Capture the Image (On your Mac)
1. Insert the SD card into your Mac.
2. Identify the disk number:
   ```bash
   diskutil list
   ```
   *(Look for the disk with the size of your SD card, e.g., /dev/disk4)*
3. Use `dd` to create the image:
   ```bash
   sudo dd if=/dev/rdiskN of=~/Desktop/aiod_master_v1.img bs=1m status=progress
   ```
   *(Replace `rdiskN` with your disk number, e.g., rdisk4)*

## 4. Compress (Optional)
```bash
gzip ~/Desktop/aiod_master_v1.img
```

You now have a `.img.gz` file you can flash to any number of cards using Raspberry Pi Imager!
